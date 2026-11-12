-- Pregunta de negocio: ¿cuánta energía vendió EnerAndes cada año y qué peso tiene cada segmento?
select
    m.anio,
    s.segmento,
    round(sum(f.energia_kwh) / 1e6, 1)                                                      as energia_gwh,
    round(sum(f.valor_cop) / 1e9, 1)                                                        as facturado_miles_de_millones_cop,
    round(100 * sum(f.energia_kwh) / sum(sum(f.energia_kwh)) over (partition by m.anio), 1) as pct_del_anio
from fact_ventas_mensual as f
join dim_mes as m on m.mes_id = f.mes_id
join dim_segmento as s on s.segmento_id = f.segmento_id
group by m.anio, s.segmento
order by m.anio, energia_gwh desc;
