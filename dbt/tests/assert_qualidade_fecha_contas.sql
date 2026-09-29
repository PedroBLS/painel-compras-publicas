-- Falha se total - excluídos != válidos (nenhum registro some ou aparece sem explicação).
select *
from {{ ref('mart_qualidade') }}
where total - excluidas_estimado_acima_1bi - excluidas_economia_fora_0_90 <> validas
