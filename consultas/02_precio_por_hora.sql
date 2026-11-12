-- Perfil horario del precio de bolsa: ¿cual es la hora mas cara del dia?
-- Hour01 corresponde a la franja 00:00-01:00, por eso restamos 1.

WITH precio_hora AS (
    UNPIVOT read_parquet('data/bronze/xm_precio_bolsa.parquet')
    ON COLUMNS('^Hour')
    INTO NAME hora VALUE precio
)
SELECT CAST(substr(hora, 5) AS INTEGER) - 1          AS hora_inicio,
       ROUND(AVG(TRY_CAST(precio AS DOUBLE)), 0)     AS precio_promedio_cop_kwh,
       ROUND(MAX(TRY_CAST(precio AS DOUBLE)), 0)     AS precio_maximo_cop_kwh
FROM precio_hora
GROUP BY hora_inicio
ORDER BY precio_promedio_cop_kwh DESC
LIMIT 5;
