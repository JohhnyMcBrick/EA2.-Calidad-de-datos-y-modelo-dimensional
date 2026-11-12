select
    cast(replace(v.periodo, '-', '') as integer)    as mes_id,
    v.divipola                                      as municipio_id,
    s.segmento_id,
    v.tipo_compra,
    v.energia_kwh,
    v.valor_cop,
    v.clientes
from {{ ref('stg_ventas') }} as v
join {{ ref('dim_segmento') }} as s
    on v.segmento = s.segmento
