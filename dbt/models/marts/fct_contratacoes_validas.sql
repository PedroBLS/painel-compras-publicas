-- Regras de qualidade (decididas após conferir a carga de 04-09/2026):
--   1. valor estimado acima de R$ 1 bilhão é tratado como erro de digitação;
--   2. onde há estimado e homologado, economia fora de 0% a 90% é inconsistente.
select
    *,
    case
        when valor_estimado > 0 and valor_homologado > 0
        then (valor_estimado - valor_homologado) / valor_estimado
    end as economia_pct
from {{ ref('stg_contratacoes') }}
where (valor_estimado is null or valor_estimado <= 1e9)
  and not coalesce(
      valor_estimado > 0 and valor_homologado > 0
      and (valor_homologado > valor_estimado or valor_homologado < valor_estimado * 0.1),
      false
  )
