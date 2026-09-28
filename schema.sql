-- Contratações públicas (Lei 14.133/2021) publicadas no PNCP,
-- via API de Dados Abertos do Compras.gov.br.

CREATE TABLE IF NOT EXISTS contratacoes (
    id_compra              TEXT PRIMARY KEY,
    numero_controle_pncp   TEXT,
    orgao_cnpj             TEXT,
    orgao_nome             TEXT,
    esfera                 TEXT,        -- F federal, E estadual, M municipal, D distrital, N não informado
    poder                  TEXT,        -- código do poder no PNCP (E executivo, L legislativo, J judiciário, N não informado)
    unidade_nome           TEXT,
    uf                     CHAR(2),
    municipio              TEXT,
    codigo_ibge            TEXT,
    modalidade             TEXT,
    amparo_legal           TEXT,
    srp                    BOOLEAN,     -- sistema de registro de preços
    objeto                 TEXT,
    situacao               TEXT,
    valor_estimado         NUMERIC(18, 2),
    valor_homologado       NUMERIC(18, 2),
    data_publicacao        TIMESTAMP NOT NULL,
    data_abertura          TIMESTAMP,
    data_encerramento      TIMESTAMP,
    data_atualizacao       TIMESTAMP,
    carregado_em           TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_contratacoes_data ON contratacoes (data_publicacao);
CREATE INDEX IF NOT EXISTS ix_contratacoes_uf ON contratacoes (uf);

-- Regras de qualidade (decididas após conferir a carga de 04-09/2026):
-- a fonte traz valores digitados errado (ex.: dispensa estimada em R$ 3,9 trilhões e
-- homologada em R$ 60 mil). Os dados brutos ficam em `contratacoes`; o painel usa esta view.
--   1. valor estimado acima de R$ 1 bilhão é tratado como erro de digitação;
--   2. onde há estimado e homologado, economia fora de 0% a 90% é tratada como inconsistente.
CREATE OR REPLACE VIEW vw_contratacoes_validas AS
SELECT *
FROM contratacoes
WHERE (valor_estimado IS NULL OR valor_estimado <= 1e9)
  -- COALESCE: sem homologado a regra 2 não se aplica (NOT NULL descartaria a linha).
  AND NOT COALESCE(
      valor_estimado > 0 AND valor_homologado > 0
      AND (valor_homologado > valor_estimado OR valor_homologado < valor_estimado * 0.1),
      false
  );

CREATE OR REPLACE VIEW vw_qualidade AS
SELECT
    count(*) AS total,
    count(*) FILTER (WHERE valor_estimado > 1e9) AS excluidas_estimado_acima_1bi,
    count(*) FILTER (WHERE valor_estimado <= 1e9 AND valor_estimado > 0 AND valor_homologado > 0
                       AND (valor_homologado > valor_estimado OR valor_homologado < valor_estimado * 0.1))
        AS excluidas_economia_fora_0_90,
    (SELECT count(*) FROM vw_contratacoes_validas) AS validas
FROM contratacoes;

-- Economia só faz sentido onde houve homologação e havia valor estimado.
CREATE OR REPLACE VIEW vw_economia AS
SELECT
    id_compra,
    date_trunc('month', data_publicacao)::date AS mes,
    uf,
    esfera,
    modalidade,
    orgao_nome,
    valor_estimado,
    valor_homologado,
    valor_estimado - valor_homologado AS economia,
    (valor_estimado - valor_homologado) / NULLIF(valor_estimado, 0) AS economia_pct
FROM vw_contratacoes_validas
WHERE valor_homologado > 0 AND valor_estimado > 0;

CREATE OR REPLACE VIEW vw_resumo_mensal AS
SELECT
    date_trunc('month', data_publicacao)::date AS mes,
    modalidade,
    count(*)              AS compras,
    sum(valor_estimado)   AS valor_estimado,
    sum(valor_homologado) AS valor_homologado
FROM vw_contratacoes_validas
GROUP BY 1, 2;
