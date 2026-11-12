with catalogo as (
    select
        codigo_recurso      as recurso_id,
        nombre_recurso,
        tipo_recurso,
        estado,
        fecha_operacion,
        true                as en_catalogo
    from {{ ref('stg_recursos') }}
),

usados as (
    select distinct codigo_recurso from {{ ref('stg_generacion') }}
),

sin_catalogo as (
    select
        u.codigo_recurso    as recurso_id,
        'Sin catálogo'      as nombre_recurso,
        'NO CATALOGADO'     as tipo_recurso,
        null                as estado,
        null                as fecha_operacion,
        false               as en_catalogo
    from usados as u
    left join catalogo as c on c.recurso_id = u.codigo_recurso
    where c.recurso_id is null
)

select * from catalogo
union all
select * from sin_catalogo
