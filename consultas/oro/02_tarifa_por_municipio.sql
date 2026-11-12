-- Pregunta de negocio: ¿qué municipios concentran las ventas y a qué tarifa media se factura en cada uno?
select
    d.municipio,
    round(sum(f.energia_kwh) / 1e6, 1)              as energia_gwh,
    round(sum(f.valor_cop) / sum(f.energia_kwh), 0) as tarifa_media_cop_kwh
from fact_ventas_mensual as f
join dim_municipio as d on d.municipio_id = f.municipio_id
where f.valor_cop is not null
group by d.municipio
order by energia_gwh desc
limit 10;
