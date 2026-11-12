select
    cast(strftime(coalesce(e.fecha, a.fecha), '%Y%m%d') as integer) as fecha_id,
    e.embalses_pct,
    a.aportes_kwh
from {{ ref('stg_embalses') }} as e
full outer join {{ ref('stg_aportes') }} as a
    on e.fecha = a.fecha
