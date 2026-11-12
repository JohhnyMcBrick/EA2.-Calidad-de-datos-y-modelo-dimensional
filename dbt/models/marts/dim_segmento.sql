select
    row_number() over (order by segmento)   as segmento_id,
    segmento
from (select distinct segmento from {{ ref('stg_ventas') }})
