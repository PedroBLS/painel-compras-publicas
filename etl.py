"""ETL de contratações públicas (PNCP) -> PostgreSQL (Supabase).

Extrai da API de Dados Abertos do Compras.gov.br, dia a dia e por modalidade,
trata os campos e grava com upsert (reprocessar um dia não duplica nada).

Uso:
    python etl.py                       # incremental: do último dia carregado até hoje
    python etl.py --inicio 2026-03-01   # carga a partir de uma data
    python etl.py --csv amostra.csv --inicio 2026-09-01 --fim 2026-09-02   # sem banco
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta

import requests

API = "https://dadosabertos.compras.gov.br/modulo-contratacoes/1_consultarContratacoes_PNCP_14133"
# A API só retorna estas modalidades: 3 Concorrência Eletrônica, 5 Pregão Eletrônico,
# 6 Dispensa, 7 Inexigibilidade (as demais vieram sempre vazias em testes de 08-09/2026).
# O código 3 também traz "Concorrência - Presencial".
MODALIDADES = (3, 5, 6, 7)
TAMANHO_PAGINA = 500  # máximo aceito pela API (1000 retorna 400)
DIAS_CARGA_INICIAL = 180

COLUNAS = [
    "id_compra", "numero_controle_pncp", "orgao_cnpj", "orgao_nome", "esfera", "poder",
    "unidade_nome", "uf", "municipio", "codigo_ibge", "modalidade", "amparo_legal", "srp",
    "objeto", "situacao", "valor_estimado", "valor_homologado", "data_publicacao",
    "data_abertura", "data_encerramento", "data_atualizacao",
]


def get_json(params: dict, tentativas: int = 6) -> dict:
    """GET com backoff exponencial em 429/5xx/timeout; a API oscila em horário de pico."""
    espera = 2
    for tentativa in range(tentativas):
        try:
            r = requests.get(API, params=params, timeout=90)
            if r.status_code == 200:
                return r.json()
            if r.status_code not in (429, 500, 502, 503, 504):
                r.raise_for_status()
        except (requests.Timeout, requests.ConnectionError):
            pass
        if tentativa == tentativas - 1:
            raise RuntimeError(f"API falhou após {tentativas} tentativas: {params}")
        time.sleep(espera)
        espera = min(espera * 2, 60)


def extrair_dia(dia: date, modalidade: int):
    """Todas as contratações publicadas em `dia` (a data final da API é exclusiva)."""
    pagina = 1
    while True:
        dados = get_json({
            "pagina": pagina,
            "tamanhoPagina": TAMANHO_PAGINA,
            "dataPublicacaoPncpInicial": dia.isoformat(),
            "dataPublicacaoPncpFinal": (dia + timedelta(days=1)).isoformat(),
            "codigoModalidade": modalidade,
        })
        yield from dados.get("resultado") or []
        if pagina >= (dados.get("totalPaginas") or 0):
            return
        pagina += 1


def _data(v):
    return datetime.fromisoformat(v) if v else None


def _texto(v):
    return " ".join(v.split()) if isinstance(v, str) and v.strip() else None


def transformar(r: dict):
    """Registro da API -> linha da tabela. Retorna None para compras excluídas ou sem id."""
    if r.get("contratacaoExcluida") or not r.get("idCompra"):
        return None
    return {
        "id_compra": r["idCompra"],
        "numero_controle_pncp": r.get("numeroControlePNCP"),
        "orgao_cnpj": r.get("orgaoEntidadeCnpj"),
        "orgao_nome": _texto(r.get("orgaoEntidadeRazaoSocial")),
        "esfera": r.get("orgaoEntidadeEsferaId"),
        "poder": r.get("orgaoEntidadePoderId"),
        "unidade_nome": _texto(r.get("unidadeOrgaoNomeUnidade")),
        "uf": r.get("unidadeOrgaoUfSigla"),
        "municipio": _texto(r.get("unidadeOrgaoMunicipioNome")),
        "codigo_ibge": r.get("unidadeOrgaoCodigoIbge"),
        "modalidade": r.get("modalidadeNome"),
        "amparo_legal": r.get("amparoLegalNome"),
        "srp": r.get("srp"),
        "objeto": _texto(r.get("objetoCompra")),
        "situacao": r.get("situacaoCompraNomePncp"),
        "valor_estimado": r.get("valorTotalEstimado"),
        "valor_homologado": r.get("valorTotalHomologado"),
        "data_publicacao": _data(r.get("dataPublicacaoPncp")),
        "data_abertura": _data(r.get("dataAberturaPropostaPncp")),
        "data_encerramento": _data(r.get("dataEncerramentoPropostaPncp")),
        "data_atualizacao": _data(r.get("dataAtualizacaoPncp")),
    }


def dias(inicio: date, fim: date):
    d = inicio
    while d <= fim:
        yield d
        d += timedelta(days=1)


UPSERT = (
    f"INSERT INTO contratacoes ({', '.join(COLUNAS)}) VALUES ({', '.join('%(' + c + ')s' for c in COLUNAS)}) "
    f"ON CONFLICT (id_compra) DO UPDATE SET "
    + ", ".join(f"{c} = EXCLUDED.{c}" for c in COLUNAS if c != "id_compra")
    + ", carregado_em = now()"
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--inicio", type=date.fromisoformat)
    p.add_argument("--fim", type=date.fromisoformat, default=date.today())
    p.add_argument("--csv", help="grava em CSV em vez do banco (para testar sem Supabase)")
    a = p.parse_args(argv)
    bucket = os.environ.get("S3_BUCKET")  # na AWS, guarda também uma cópia bruta de cada dia no S3
    if bucket:
        import boto3  # já vem instalado no ambiente do Lambda

        s3 = boto3.client("s3")

    conn = None
    if not a.csv:
        import psycopg
        from dotenv import load_dotenv

        load_dotenv()
        url = os.environ.get("DATABASE_URL")
        if not url:
            sys.exit("Defina DATABASE_URL no arquivo .env (veja .env.example).")
        conn = psycopg.connect(url)
        with conn.cursor() as cur:
            cur.execute(open("schema.sql", encoding="utf-8").read())
            cur.execute("SELECT max(data_publicacao)::date FROM contratacoes")
            ultimo = cur.fetchone()[0]
        conn.commit()
        # Reprocessa o último dia carregado: ele pode ter sido carregado pela metade.
        inicio = a.inicio or ultimo or (a.fim - timedelta(days=DIAS_CARGA_INICIAL))
    else:
        inicio = a.inicio or a.fim

    escritor = None
    if a.csv:
        arq = open(a.csv, "w", newline="", encoding="utf-8")
        escritor = csv.DictWriter(arq, fieldnames=COLUNAS)
        escritor.writeheader()

    total = 0
    for dia in dias(inicio, a.fim):
        linhas = [t for m in MODALIDADES for r in extrair_dia(dia, m) if (t := transformar(r))]
        if escritor:
            escritor.writerows(linhas)
        elif linhas:
            with conn.cursor() as cur:
                cur.executemany(UPSERT, linhas)
            conn.commit()  # commit por dia: uma falha não perde os dias anteriores
        if bucket and linhas:
            corpo = "\n".join(json.dumps(l, default=str, ensure_ascii=False) for l in linhas)
            s3.put_object(Bucket=bucket, Key=f"contratacoes/dia={dia}.jsonl", Body=corpo.encode("utf-8"))
        total += len(linhas)
        print(f"{dia}: {len(linhas)} contratações (acumulado {total})", flush=True)

    if conn:
        conn.close()
    if escritor:
        arq.close()
    print(f"Concluído: {total} contratações de {inicio} a {a.fim}.")


if __name__ == "__main__":
    main()
