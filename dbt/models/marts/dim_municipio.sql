select distinct
    divipola        as municipio_id,
    municipio,
    'Antioquia'     as departamento
from {{ ref('stg_ventas') }}
