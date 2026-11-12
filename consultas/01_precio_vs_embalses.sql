-- Precio de bolsa promedio mensual frente al nivel de los embalses.
-- Se consulta DIRECTO sobre los Parquet de bronce: no hay base de datos.
-- En bronce los valores vienen como TEXTO, por eso usamos TRY_CAST
-- (si un valor viene vacio, devuelve NULL en vez de fallar).

WITH precio_hora AS (
    -- XM entrega el precio en formato ANCHO (Hour01 ... Hour24).
    -- UNPIVOT lo pasa a formato LARGO: una fila por fecha y hora.
    UNPIVOT read_parquet('data/bronze/xm_precio_bolsa.parquet')
    ON COLUMNS('^Hour')
    INTO NAME hora VALUE precio
),
precio_mes AS (
    SELECT strftime(CAST("Date" AS DATE), '%Y-%m')          AS mes,
           ROUND(AVG(TRY_CAST(precio AS DOUBLE)), 0)        AS precio_bolsa_cop_kwh
    FROM precio_hora
    GROUP BY mes
),
embalses_mes AS (
    SELECT strftime(CAST("Date" AS DATE), '%Y-%m')          AS mes,
           ROUND(AVG(TRY_CAST("Value" AS DOUBLE)) * 100, 1) AS embalses_pct
    FROM read_parquet('data/bronze/xm_embalses.parquet')
    GROUP BY mes
)
SELECT p.mes, p.precio_bolsa_cop_kwh, e.embalses_pct
FROM precio_mes p
JOIN embalses_mes e USING (mes)
ORDER BY p.mes;
