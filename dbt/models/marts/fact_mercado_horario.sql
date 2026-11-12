select
    cast(strftime(coalesce(p.fecha, d.fecha), '%Y%m%d') as integer) * 100 + coalesce(p.hora, d.hora) as mercado_hora_id,
    cast(strftime(coalesce(p.fecha, d.fecha), '%Y%m%d') as integer)                                  as fecha_id,
    coalesce(p.hora, d.hora)                                                                         as hora,
    p.precio_cop_kwh                                                                                 as precio_bolsa_cop_kwh,
    d.demanda_kwh
from {{ ref('stg_precio_bolsa') }} as p
full outer join {{ ref('stg_demanda') }} as d
    on p.fecha = d.fecha and p.hora = d.hora
