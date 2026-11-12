# Diccionario de datos de la capa oro

Una tabla por cada tabla del esquema estrella. Los tipos de dato se leen de `data/observatorio.duckdb`; este archivo se genera con `python -m src.documentar`.

## dim_fecha

Un día. Calendario del proyecto con la fase ENSO del mes.

| Columna | Tipo de dato | Descripción | Origen |
|---|---|---|---|
| fecha_id | INTEGER | Llave del día en formato AAAAMMDD. | Calculada en dbt/models/marts/dim_fecha.sql |
| fecha | DATE | Fecha del día. | Serie de días entre las variables fecha_inicio y fecha_fin de dbt_project.yml |
| mes_id | INTEGER | Llave del mes en formato AAAAMM. | Calculada a partir de la fecha |
| anio | BIGINT | Año de la fecha. | Calculada a partir de la fecha |
| mes | BIGINT | Número del mes, de 1 a 12. | Calculada a partir de la fecha |
| nombre_mes | VARCHAR | Nombre del mes en español. | Calculada a partir de la fecha |
| trimestre | BIGINT | Trimestre del año, de 1 a 4. | Calculada a partir de la fecha |
| dia_del_mes | BIGINT | Día del mes. | Calculada a partir de la fecha |
| dia_semana | BIGINT | Día de la semana, de 1 (lunes) a 7 (domingo). | Calculada a partir de la fecha |
| nombre_dia | VARCHAR | Nombre del día de la semana en español. | Calculada a partir de la fecha |
| es_fin_de_semana | BOOLEAN | Verdadero si el día es sábado o domingo. | Calculada a partir de la fecha |
| oni | DOUBLE | Índice ONI del mes. Vacío si NOAA aún no lo publica. | silver/noaa_oni.parquet, columna oni |
| fase_enso | VARCHAR | El Niño, La Niña, Neutral o Sin dato. | silver/noaa_oni.parquet, columna fase_enso |

## dim_mes

Un mes. Se obtiene de dim_fecha.

| Columna | Tipo de dato | Descripción | Origen |
|---|---|---|---|
| mes_id | INTEGER | Llave del mes en formato AAAAMM. | dim_fecha.mes_id |
| periodo | VARCHAR | Mes en formato AAAA-MM. | dim_fecha.fecha |
| anio | BIGINT | Año del mes. | dim_fecha.anio |
| mes | BIGINT | Número del mes, de 1 a 12. | dim_fecha.mes |
| nombre_mes | VARCHAR | Nombre del mes en español. | dim_fecha.nombre_mes |
| trimestre | BIGINT | Trimestre del año. | dim_fecha.trimestre |
| oni | DOUBLE | Índice ONI del mes. | dim_fecha.oni |
| fase_enso | VARCHAR | Fase del fenómeno en el mes. | dim_fecha.fase_enso |

## dim_municipio

Un municipio de Antioquia con su código DIVIPOLA.

| Columna | Tipo de dato | Descripción | Origen |
|---|---|---|---|
| municipio_id | VARCHAR | Código DIVIPOLA de 5 dígitos. | silver/enerandes_ventas.parquet, columna divipola |
| municipio | VARCHAR | Nombre oficial del municipio. | silver/enerandes_ventas.parquet, columna municipio |
| departamento | VARCHAR | Departamento del municipio. | Constante: Antioquia |

## dim_segmento

Un segmento de cliente.

| Columna | Tipo de dato | Descripción | Origen |
|---|---|---|---|
| segmento_id | BIGINT | Número del segmento, asignado en orden alfabético. | Calculada en dbt |
| segmento | VARCHAR | Residencial, Comercial, Industrial o No informado. | silver/enerandes_ventas.parquet, columna segmento |

## dim_recurso

Una planta de generación.

| Columna | Tipo de dato | Descripción | Origen |
|---|---|---|---|
| recurso_id | VARCHAR | Código SIC de la planta. | silver/xm_recursos.parquet, columna codigo_recurso |
| nombre_recurso | VARCHAR | Nombre de la planta. | silver/xm_recursos.parquet, columna nombre_recurso |
| tipo_recurso | VARCHAR | Tipo de planta: hidráulica, térmica, eólica, solar u otro. | silver/xm_recursos.parquet, columna tipo_recurso |
| estado | VARCHAR | Estado operativo de la planta. | silver/xm_recursos.parquet, columna estado |
| fecha_operacion | TIMESTAMP | Fecha de inicio de operación. | silver/xm_recursos.parquet, columna fecha_operacion |
| en_catalogo | BOOLEAN | Falso si la planta genera pero no está en ListadoRecursos. | Calculada en dbt |

## dim_estacion

Una estación meteorológica del IDEAM.

| Columna | Tipo de dato | Descripción | Origen |
|---|---|---|---|
| estacion_id | VARCHAR | Código de la estación. | silver/ideam_precipitacion.parquet, columna codigo_estacion |
| estacion | VARCHAR | Nombre de la estación. | silver/ideam_precipitacion.parquet, columna estacion |
| municipio | VARCHAR | Municipio donde está la estación. | silver/ideam_precipitacion.parquet, columna municipio |
| latitud | DOUBLE | Latitud en grados decimales. | silver/ideam_precipitacion.parquet, columna latitud |
| longitud | DOUBLE | Longitud en grados decimales. | silver/ideam_precipitacion.parquet, columna longitud |

## fact_ventas_mensual

Grano: un mes, un municipio, un segmento y un tipo de compra.

| Columna | Tipo de dato | Descripción | Origen |
|---|---|---|---|
| mes_id | INTEGER | Llave a dim_mes. | silver/enerandes_ventas.parquet, columna periodo |
| municipio_id | VARCHAR | Llave a dim_municipio. | silver/enerandes_ventas.parquet, columna divipola |
| segmento_id | BIGINT | Llave a dim_segmento. | dim_segmento.segmento_id |
| tipo_compra | VARCHAR | Bolsa o Contrato. | silver/enerandes_ventas.parquet, columna tipo_compra |
| energia_kwh | DOUBLE | Energía vendida en kWh. | silver/enerandes_ventas.parquet, columna energia_kwh |
| valor_cop | DOUBLE | Valor facturado en pesos. Puede estar vacío. | silver/enerandes_ventas.parquet, columna valor_cop |
| clientes | BIGINT | Número de clientes del mes. | silver/enerandes_ventas.parquet, columna clientes |

## fact_mercado_horario

Grano: una hora de un día en el sistema interconectado nacional.

| Columna | Tipo de dato | Descripción | Origen |
|---|---|---|---|
| mercado_hora_id | BIGINT | Llave de la hora: AAAAMMDD por 100 más la hora. | Calculada en dbt |
| fecha_id | INTEGER | Llave a dim_fecha. | silver/xm_precio_bolsa.parquet, columna fecha |
| hora | BIGINT | Hora de inicio de la franja, de 0 a 23. | silver/xm_precio_bolsa.parquet, columna hora |
| precio_bolsa_cop_kwh | DOUBLE | Precio de bolsa nacional en pesos por kWh. | silver/xm_precio_bolsa.parquet, columna precio_cop_kwh |
| demanda_kwh | DOUBLE | Demanda real del sistema en kWh. | silver/xm_demanda.parquet, columna demanda_kwh |

## fact_generacion_recurso

Grano: una planta en una hora de un día.

| Columna | Tipo de dato | Descripción | Origen |
|---|---|---|---|
| generacion_id | VARCHAR | Llave: fecha, hora y código de la planta. | Calculada en dbt |
| fecha_id | INTEGER | Llave a dim_fecha. | silver/xm_generacion.parquet, columna fecha |
| hora | BIGINT | Hora de inicio de la franja, de 0 a 23. | silver/xm_generacion.parquet, columna hora |
| recurso_id | VARCHAR | Llave a dim_recurso. | silver/xm_generacion.parquet, columna codigo_recurso |
| generacion_kwh | DOUBLE | Generación de la planta en kWh. | silver/xm_generacion.parquet, columna generacion_kwh |

## fact_hidrologia_diaria

Grano: un día.

| Columna | Tipo de dato | Descripción | Origen |
|---|---|---|---|
| fecha_id | INTEGER | Llave a dim_fecha. | silver/xm_embalses.parquet, columna fecha |
| embalses_pct | DOUBLE | Porcentaje de volumen útil de los embalses. | silver/xm_embalses.parquet, columna embalses_pct |
| aportes_kwh | DOUBLE | Aportes hídricos de energía en kWh. | silver/xm_aportes.parquet, columna aportes_kwh |

## fact_clima_diario

Grano: una estación del IDEAM en un día.

| Columna | Tipo de dato | Descripción | Origen |
|---|---|---|---|
| clima_id | VARCHAR | Llave: fecha y código de la estación. | Calculada en dbt |
| fecha_id | INTEGER | Llave a dim_fecha. | silver/ideam_precipitacion.parquet, columna fecha |
| estacion_id | VARCHAR | Llave a dim_estacion. | silver/ideam_precipitacion.parquet, columna codigo_estacion |
| precipitacion_mm | DOUBLE | Precipitación del día en milímetros. | silver/ideam_precipitacion.parquet, columna precipitacion_mm |
| temperatura_c | DOUBLE | Temperatura del día en grados Celsius. | silver/ideam_temperatura.parquet, columna temperatura_c |
