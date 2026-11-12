-- Pregunta de negocio: ¿qué parte de la energía se compra en bolsa frente a contrato y a qué tarifa?
-- La compra en bolsa es la más expuesta al precio de bolsa durante El Niño.
select
    m.anio,
    f.tipo_compra,
    round(sum(f.energia_kwh) / 1e6, 1)                                                      as energia_gwh,
    round(100 * sum(f.energia_kwh) / sum(sum(f.energia_kwh)) over (partition by m.anio), 1) as pct_energia_del_anio,
    round(sum(f.valor_cop) / sum(f.energia_kwh), 0)                                         as tarifa_media_cop_kwh
from fact_ventas_mensual as f
join dim_mes as m on m.mes_id = f.mes_id
where f.valor_cop is not null
group by m.anio, f.tipo_compra
order by m.anio, f.tipo_compra;
