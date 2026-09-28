from datetime import date, datetime

import etl

REGISTRO = {
    "idCompra": "15830106000342026",
    "numeroControlePNCP": "05055128000176-1-000108/2026",
    "orgaoEntidadeCnpj": "05055128000176",
    "orgaoEntidadeRazaoSocial": "UNIVERSIDADE FEDERAL  DE CAMPINA GRANDE ",
    "orgaoEntidadeEsferaId": "F",
    "orgaoEntidadePoderId": "E",
    "unidadeOrgaoNomeUnidade": "CENTRO DE CIENCIAS",
    "unidadeOrgaoUfSigla": "PB",
    "unidadeOrgaoMunicipioNome": "POMBAL",
    "unidadeOrgaoCodigoIbge": "2512101",
    "modalidadeNome": "Dispensa",
    "amparoLegalNome": "Lei 14.133/2021, Art. 75, III, a",
    "srp": False,
    "objetoCompra": "Aquisição de\nmaterial   de consumo",
    "situacaoCompraNomePncp": "Divulgada no PNCP",
    "valorTotalEstimado": 6351.15,
    "valorTotalHomologado": 6195.2,
    "dataPublicacaoPncp": "2026-09-01T07:26:01",
    "dataAberturaPropostaPncp": "2026-09-01T08:00:00",
    "dataEncerramentoPropostaPncp": None,
    "dataAtualizacaoPncp": "2026-09-01T07:26:01",
    "contratacaoExcluida": False,
}


def test_transformar_mapeia_e_limpa_campos():
    t = etl.transformar(REGISTRO)
    assert set(t) == set(etl.COLUNAS)
    assert t["orgao_nome"] == "UNIVERSIDADE FEDERAL DE CAMPINA GRANDE"
    assert t["objeto"] == "Aquisição de material de consumo"
    assert t["data_publicacao"] == datetime(2026, 9, 1, 7, 26, 1)
    assert t["data_encerramento"] is None
    assert t["valor_homologado"] == 6195.2


def test_transformar_descarta_excluidas_e_sem_id():
    assert etl.transformar({**REGISTRO, "contratacaoExcluida": True}) is None
    assert etl.transformar({**REGISTRO, "idCompra": None}) is None


def test_dias_inclui_inicio_e_fim():
    assert list(etl.dias(date(2026, 9, 1), date(2026, 9, 3))) == [
        date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3)
    ]


def test_extrair_dia_pagina_e_usa_fim_exclusivo(monkeypatch):
    chamadas = []

    def falso(params):
        chamadas.append(params)
        return {"resultado": [{"idCompra": str(params["pagina"])}], "totalPaginas": 2}

    monkeypatch.setattr(etl, "get_json", falso)
    ids = [r["idCompra"] for r in etl.extrair_dia(date(2026, 9, 1), 6)]
    assert ids == ["1", "2"]
    assert chamadas[0]["dataPublicacaoPncpFinal"] == "2026-09-02"
