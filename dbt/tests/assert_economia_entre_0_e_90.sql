-- Falha se algum registro válido tiver economia fora da faixa 0%-90%.
select id_compra, economia_pct
from {{ ref('fct_contratacoes_validas') }}
where economia_pct < 0 or economia_pct > 0.9
