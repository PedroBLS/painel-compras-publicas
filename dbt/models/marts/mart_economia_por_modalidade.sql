select
    modalidade,
    count(*) as compras,
    sum(valor_estimado) as valor_estimado,
    sum(valor_homologado) as valor_homologado,
    percentile_cont(0.5) within group (order by economia_pct)
        filter (where economia_pct is not null) as economia_mediana_pct
from {{ ref('fct_contratacoes_validas') }}
group by modalidade
