-- Pregunta de negocio: ¿cuánta energía aporta cada tipo de planta y cómo se mueve el nivel de los embalses?
select
    r.tipo_recurso,
    count(distinct r.recurso_id)                    as plantas,
    round(sum(g.generacion_kwh) / 1e6, 1)           as generacion_gwh,
    round(100 * sum(g.generacion_kwh) / sum(sum(g.generacion_kwh)) over (), 1) as pct_del_total
from fact_generacion_recurso as g
join dim_recurso as r on r.recurso_id = g.recurso_id
group by r.tipo_recurso
order by generacion_gwh desc;
