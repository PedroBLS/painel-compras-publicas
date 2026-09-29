-- Falha se algum registro válido tiver valor estimado acima de R$ 1 bilhão.
select id_compra, valor_estimado
from {{ ref('fct_contratacoes_validas') }}
where valor_estimado > 1e9
