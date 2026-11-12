select
    cast(strftime(fecha, '%Y%m%d') as varchar) || '-' || lpad(cast(hora as varchar), 2, '0') || '-' || codigo_recurso as generacion_id,
    cast(strftime(fecha, '%Y%m%d') as integer)  as fecha_id,
    hora,
    codigo_recurso                              as recurso_id,
    generacion_kwh
from {{ ref('stg_generacion') }}
