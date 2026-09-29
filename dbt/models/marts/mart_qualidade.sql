-- Quantos registros cada regra de qualidade excluiu (recalculado a cada dbt build).
select
    (select count(*) from {{ ref('stg_contratacoes') }}) as total,
    (select count(*) from {{ ref('stg_contratacoes') }} where valor_estimado > 1e9)
        as excluidas_estimado_acima_1bi,
    (select count(*) from {{ ref('stg_contratacoes') }}
      where valor_estimado <= 1e9 and valor_estimado > 0 and valor_homologado > 0
        and (valor_homologado > valor_estimado or valor_homologado < valor_estimado * 0.1))
        as excluidas_economia_fora_0_90,
    (select count(*) from {{ ref('fct_contratacoes_validas') }}) as validas
