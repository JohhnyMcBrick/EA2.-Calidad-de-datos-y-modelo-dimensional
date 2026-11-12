-- Pregunta de negocio: ¿cómo cambia el precio de bolsa y la demanda según la fase de El Niño o La Niña?
select
    d.fase_enso,
    count(distinct d.fecha_id)                                  as dias,
    round(avg(f.precio_bolsa_cop_kwh), 0)                       as precio_bolsa_promedio_cop_kwh,
    round(max(f.precio_bolsa_cop_kwh), 0)                       as precio_bolsa_maximo_cop_kwh,
    round(avg(f.demanda_kwh) / 1e6, 2)                          as demanda_promedio_gwh_hora
from fact_mercado_horario as f
join dim_fecha as d on d.fecha_id = f.fecha_id
group by d.fase_enso
order by precio_bolsa_promedio_cop_kwh desc;
