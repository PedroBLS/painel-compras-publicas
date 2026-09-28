# Painel de Compras Públicas (PNCP)

Pipeline de dados que coleta as **contratações públicas da Lei 14.133/2021** publicadas no PNCP, grava num **PostgreSQL (Supabase)** e alimenta um **dashboard no Power BI**. O painel mostra volume, valores e economia (estimado × homologado) por modalidade, órgão, UF e mês.

```
API Dados Abertos Compras.gov.br ──► etl.py (Python) ──► PostgreSQL (Supabase) ──► Power BI
      (PNCP, Lei 14.133)             extração diária       tabela + views          dashboard
```

## Fonte dos dados

[API de Dados Abertos do Compras.gov.br](https://dadosabertos.compras.gov.br/), no módulo de contratações do PNCP (endpoint `1_consultarContratacoes_PNCP_14133`). É pública e não exige cadastro.

O que foi descoberto testando a API e está tratado no ETL:
- A data final da consulta é **exclusiva**. Para pegar um dia, a consulta vai de `dia` até `dia + 1`.
- As páginas têm no máximo **500 registros**. Com `tamanhoPagina=1000`, a API responde erro 400.
- A API só retorna as modalidades **3** (Concorrência), **5** (Pregão Eletrônico), **6** (Dispensa) e **7** (Inexigibilidade).
- O volume é de cerca de **1.300 contratações por dia útil** no Brasil inteiro (01/09/2026: 1.323).

## ETL (`etl.py`)

- **Extração:** dia a dia e por modalidade, com paginação. Em erros 429/5xx e timeouts, tenta de novo com espera crescente (backoff exponencial).
- **Tratamento:**
  - descarta as compras marcadas como excluídas;
  - normaliza espaços nos textos;
  - converte as datas;
  - renomeia os campos para snake_case em português.
- **Carga:** faz *upsert* por `id_compra`, então reprocessar um dia não duplica registros. O commit é feito dia a dia, para que uma falha não perca os dias já carregados.
- **Incremental:** sem argumentos, recomeça do último dia carregado. Na primeira execução, carrega os últimos 180 dias.

O schema (`schema.sql`) cria a tabela `contratacoes` (dados brutos) e as views:
- `vw_contratacoes_validas` e `vw_qualidade`: regras de qualidade (veja abaixo);
- `vw_economia`: economia em R$ e em %, só para compras válidas com valor estimado e homologado;
- `vw_resumo_mensal`: quantidade de compras e valores por mês e modalidade.

## Qualidade dos dados

Depois da primeira carga (155.169 contratações, de 01/04 a 24/09/2026), apareceram valores claramente digitados errado na fonte. Por exemplo, uma dispensa estimada em **R$ 3,9 trilhões** e homologada em **R$ 60 mil**. Apenas 70 registros acima de R$ 1 bilhão somavam **R$ 22,5 trilhões**, contra R$ 522 bilhões de todo o resto.

Regras aplicadas em `vw_contratacoes_validas`, sem apagar nada da tabela bruta:

| Regra | Registros excluídos |
|---|---|
| Valor estimado acima de R$ 1 bilhão | 70 |
| Economia fora de 0% a 90% (homologado maior que o estimado ou menor que 10% dele) | 4.399 |
| **Válidos para o painel** | **150.700** |

A view `vw_qualidade` recalcula esses números a cada carga. Mesmo depois do filtro, a economia é assimétrica: **mediana de 2,0%** contra média de 15,8%. Por isso o painel usa a mediana.

Outro ponto de atenção: nos meses mais recentes, o valor homologado é menor porque muitos processos ainda não terminaram. A comparação entre meses deve considerar isso.

## Como executar

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
pytest                            # testes do tratamento e da paginação (não usam rede)

# Teste sem banco: um dia em CSV
python etl.py --csv amostra.csv --inicio 2026-09-01 --fim 2026-09-01

# Carga no Supabase
copy .env.example .env            # e preencha DATABASE_URL
python etl.py
```

A connection string fica **somente** no `.env`, que está no `.gitignore`.

## Dashboard (Power BI)

Conexão: **Obter dados → Banco de dados PostgreSQL**. Use o host e a porta do *Session pooler* do Supabase, com o banco `postgres`. Importe a tabela `contratacoes` e as views.

_(Prints e medidas DAX serão adicionados quando o painel estiver pronto.)_

## Tecnologias

Python (requests, psycopg), PostgreSQL / Supabase, SQL (views), pytest, Power BI.

Desenvolvido por Pedro Brandão Leal dos Santos, com apoio do **Claude Code** na escrita do código.
