"""Copia a tabela bruta `contratacoes` do PostgreSQL (Supabase) para o BigQuery (dataset `pncp`).

Uso: python load_bigquery.py
A chave da conta de serviço fica fora do repositório (padrão: ~/.gcp/dbt-bigquery.json,
ou a variável GOOGLE_APPLICATION_CREDENTIALS).
"""
import io
import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
CHAVE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", str(Path.home() / ".gcp" / "dbt-bigquery.json"))
PROJETO = json.load(open(CHAVE, encoding="utf-8"))["project_id"]
DATASET = "pncp"
LOCAL = "US"  # o sandbox gratuito do BigQuery funciona em US

SCHEMA = [bigquery.SchemaField(n, t) for n, t in [
    ("id_compra", "STRING"), ("numero_controle_pncp", "STRING"), ("orgao_cnpj", "STRING"),
    ("orgao_nome", "STRING"), ("esfera", "STRING"), ("poder", "STRING"), ("unidade_nome", "STRING"),
    ("uf", "STRING"), ("municipio", "STRING"), ("codigo_ibge", "STRING"), ("modalidade", "STRING"),
    ("amparo_legal", "STRING"), ("srp", "BOOL"), ("objeto", "STRING"), ("situacao", "STRING"),
    ("valor_estimado", "NUMERIC"), ("valor_homologado", "NUMERIC"), ("data_publicacao", "DATETIME"),
    ("data_abertura", "DATETIME"), ("data_encerramento", "DATETIME"), ("data_atualizacao", "DATETIME"),
]]


def main():
    colunas = ", ".join(f.name for f in SCHEMA)
    buffer = io.BytesIO()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        with cur.copy(f"COPY (SELECT {colunas} FROM contratacoes) TO STDOUT WITH (FORMAT csv, HEADER true)") as copia:
            for bloco in copia:
                buffer.write(bloco)
    buffer.seek(0)
    print(f"Exportado do PostgreSQL: {buffer.getbuffer().nbytes / 1e6:.1f} MB")

    client = bigquery.Client.from_service_account_json(CHAVE, project=PROJETO)
    client.create_dataset(bigquery.Dataset(f"{PROJETO}.{DATASET}"), exists_ok=True)
    job = client.load_table_from_file(
        buffer, f"{PROJETO}.{DATASET}.contratacoes", location=LOCAL,
        job_config=bigquery.LoadJobConfig(
            schema=SCHEMA, source_format=bigquery.SourceFormat.CSV, skip_leading_rows=1,
            allow_quoted_newlines=True, write_disposition="WRITE_TRUNCATE"))
    job.result()
    tabela = client.get_table(f"{PROJETO}.{DATASET}.contratacoes")
    print(f"Carregado no BigQuery: {tabela.num_rows} linhas em {PROJETO}.{DATASET}.contratacoes")


if __name__ == "__main__":
    main()
