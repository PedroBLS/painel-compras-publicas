-- A mediana muda de sintaxe entre os bancos: no PostgreSQL é agregada (within group),
-- no BigQuery percentile_cont só existe como função de janela.
{% if target.type == 'bigquery' %}
select
    modalidade,
    count(*) as compras,
    sum(valor_estimado) as valor_estimado,
    sum(valor_homologado) as valor_homologado,
    any_value(mediana) as economia_mediana_pct
from (
    select *, percentile_cont(economia_pct, 0.5) over (partition by modalidade) as mediana
    from {{ ref('fct_contratacoes_validas') }}
)
group by modalidade
{% else %}
select
    modalidade,
    count(*) as compras,
    sum(valor_estimado) as valor_estimado,
    sum(valor_homologado) as valor_homologado,
    percentile_cont(0.5) within group (order by economia_pct)
        filter (where economia_pct is not null) as economia_mediana_pct
from {{ ref('fct_contratacoes_validas') }}
group by modalidade
{% endif %}
