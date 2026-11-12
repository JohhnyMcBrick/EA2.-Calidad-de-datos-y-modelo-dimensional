select
    cast(strftime(coalesce(p.fecha, t.fecha), '%Y%m%d') as varchar) || '-' || coalesce(p.codigo_estacion, t.codigo_estacion) as clima_id,
    cast(strftime(coalesce(p.fecha, t.fecha), '%Y%m%d') as integer)     as fecha_id,
    coalesce(p.codigo_estacion, t.codigo_estacion)                      as estacion_id,
    p.precipitacion_mm,
    t.temperatura_c
from {{ ref('stg_precipitacion') }} as p
full outer join {{ ref('stg_temperatura') }} as t
    on p.fecha = t.fecha and p.codigo_estacion = t.codigo_estacion
