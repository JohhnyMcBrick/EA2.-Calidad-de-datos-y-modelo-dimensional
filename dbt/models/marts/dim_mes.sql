select distinct
    mes_id,
    strftime(fecha, '%Y-%m')    as periodo,
    anio,
    mes,
    nombre_mes,
    trimestre,
    oni,
    fase_enso
from {{ ref('dim_fecha') }}
