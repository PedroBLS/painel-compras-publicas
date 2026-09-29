-- Camada de staging: nomes legíveis para códigos da fonte, sem filtrar nada.
select
    id_compra,
    numero_controle_pncp,
    orgao_cnpj,
    orgao_nome,
    esfera,
    case esfera
        when 'F' then 'Federal'
        when 'E' then 'Estadual'
        when 'M' then 'Municipal'
        when 'D' then 'Distrital'
        else 'Não informado'
    end as esfera_nome,
    uf,
    municipio,
    modalidade,
    amparo_legal,
    srp,
    objeto,
    situacao,
    valor_estimado,
    valor_homologado,
    data_publicacao,
    data_publicacao::date as data,
    date_trunc('month', data_publicacao)::date as mes
from {{ source('pncp', 'contratacoes') }}
