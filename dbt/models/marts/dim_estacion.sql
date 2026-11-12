with observaciones as (
    select fecha, codigo_estacion, estacion, municipio, latitud, longitud from {{ ref('stg_precipitacion') }}
    union all
    select fecha, codigo_estacion, estacion, municipio, latitud, longitud from {{ ref('stg_temperatura') }}
)

select
    codigo_estacion     as estacion_id,
    estacion,
    municipio,
    latitud,
    longitud
from observaciones
qualify row_number() over (partition by codigo_estacion order by fecha desc) = 1
