# Reporte de calidad de la capa plata

Este archivo lo genera `python -m src.transformar` con las métricas que mide cada programa de limpieza. Cada regla muestra el problema, la regla aplicada y la métrica antes y después de corregirlo.

Reglas medidas en total: 32. Las reglas que no encontraron casos en los datos no se listan.

## Resumen por tabla

| Fuente | Tabla | Filas en bronce | Filas en plata | Filas en cuarentena |
|---|---|---:|---:|---:|
| EnerAndes | enerandes_ventas | 4,184 | 4,007 | 43 |
| XM | xm_precio_bolsa | 273 | 6,552 | 0 |
| XM | xm_demanda | 273 | 6,552 | 0 |
| XM | xm_generacion | 126,314 | 1,978,304 | 1,053,232 |
| XM | xm_embalses | 273 | 273 | 0 |
| XM | xm_aportes | 273 | 273 | 0 |
| XM | xm_recursos | 2,512 | 2,509 | 0 |
| IDEAM | ideam_precipitacion | 2,784 | 2,779 | 5 |
| IDEAM | ideam_temperatura | 1,708 | 1,708 | 0 |
| NOAA | noaa_oni | 921 | 921 | 0 |

Las series horarias de XM llegan con una fila por día y 24 columnas de hora; en plata quedan con una fila por hora, por eso tienen más filas que en bronce.

## EnerAndes

| # | Problema | Regla aplicada | Antes | Después |
|---|---|---|---:|---:|
| 1 | Nombres de columna distintos entre hojas | Mapear cada encabezado a un nombre estándar | 26 | 7 |
| 2 | Filas de título y notas antes del encabezado | Ubicar la fila de encabezados y descartar lo anterior | 6 | 0 |
| 3 | Filas de totales | Eliminarlas | 4 | 0 |
| 4 | Fechas en formatos distintos a AAAA-MM | Convertir mmm-aa, MM/AAAA y DD/MM/AAAA a AAAA-MM | 2704 | 0 |
| 5 | Fecha de corte día/mes/año (hoja 2026) | Leer el segundo número como mes, no como día | 834 | 0 |
| 6 | Energía en MWh mezclada con kWh | Multiplicar por 1000 para dejar todo en kWh | 347 | 0 |
| 7 | Segmento escrito de varias formas | Unificar a 3 valores | 6 | 3 |
| 8 | Segmento vacío | Marcarlo como 'No informado' | 29 | 0 |
| 9 | Tipo de compra escrito de varias formas | Unificar a Bolsa y Contrato | 4 | 2 |
| 10 | Municipio escrito de varias formas | Unificar con el nombre oficial y el código DIVIPOLA | 32 | 15 |
| 11 | Filas duplicadas | Dejar una sola copia | 120 | 0 |
| 12 | Energía vacía | Pasar la fila a cuarentena | 25 | 0 |
| 13 | Energía negativa | Pasar la fila a cuarentena | 18 | 0 |
| 14 | Valor facturado vacío | Dejarlo vacío y documentarlo | 28 | 28 |

Filas en cuarentena:

| Tabla | Motivo | Filas | Por qué no se corrige |
|---|---|---:|---|
| enerandes_ventas | Energía vacía | 25 | no hay cómo reconstruir el consumo de esa fila sin inventarlo |
| enerandes_ventas | Energía negativa | 18 | un consumo negativo es un error de captura y no se sabe cuál era el valor real |

## XM

| # | Tabla | Problema | Regla aplicada | Antes | Después |
|---|---|---|---|---:|---:|
| 1 | xm_precio_bolsa | Valores por hora en 24 columnas (Hour01 a Hour24) | Pasar a una fila por fecha y hora | 24 | 1 |
| 2 | xm_precio_bolsa | Valores guardados como texto | Convertir a número | 6552 | 0 |
| 3 | xm_demanda | Valores por hora en 24 columnas (Hour01 a Hour24) | Pasar a una fila por fecha y hora | 24 | 1 |
| 4 | xm_demanda | Valores guardados como texto | Convertir a número | 6552 | 0 |
| 5 | xm_generacion | Valores por hora en 24 columnas (Hour01 a Hour24) | Pasar a una fila por fecha y hora | 24 | 1 |
| 6 | xm_generacion | Valores guardados como texto | Convertir a número | 3031536 | 0 |
| 7 | xm_embalses | Valores guardados como texto | Convertir a número | 273 | 0 |
| 8 | xm_aportes | Valores guardados como texto | Convertir a número | 273 | 0 |
| 9 | xm_recursos | Nombres de columna del catálogo en inglés | Renombrar a nombres estándar en español | 5 | 0 |
| 10 | xm_recursos | Plantas repetidas en el catálogo | Dejar una fila por código de recurso | 3 | 0 |

Filas en cuarentena:

| Tabla | Motivo | Filas | Por qué no se corrige |
|---|---|---:|---|
| xm_generacion | Valor no numérico | 1053232 | el valor no se pudo convertir a número |

## IDEAM

| # | Tabla | Problema | Regla aplicada | Antes | Después |
|---|---|---|---|---:|---:|
| 1 | ideam_precipitacion | Fechas guardadas como texto con hora | Convertir a fecha | 2784 | 0 |
| 2 | ideam_precipitacion | Valores guardados como texto | Convertir a número | 2784 | 0 |
| 3 | ideam_precipitacion | Valores vacíos o fuera de rango físico | Pasar la fila a cuarentena | 5 | 0 |
| 4 | ideam_temperatura | Fechas guardadas como texto con hora | Convertir a fecha | 1708 | 0 |
| 5 | ideam_temperatura | Valores guardados como texto | Convertir a número | 1708 | 0 |

Filas en cuarentena:

| Tabla | Motivo | Filas | Por qué no se corrige |
|---|---|---:|---|
| ideam_precipitacion | Valor fuera de rango | 5 | supera el máximo físico razonable de la variable |

## NOAA

| # | Tabla | Problema | Regla aplicada | Antes | Después |
|---|---|---|---|---:|---:|
| 1 | noaa_oni | Año y anomalía guardados como texto | Convertir a número | 1842 | 0 |
| 2 | noaa_oni | Trimestres móviles (DJF, JFM...) | Asignar cada trimestre a su mes central (DJF -> enero) | 12 | 12 |
| 3 | noaa_oni | Meses sin fase del fenómeno | Calcular la fase con los umbrales +0,5 y -0,5 | 921 | 0 |

Filas en cuarentena:

| Tabla | Motivo | Filas | Por qué no se corrige |
|---|---|---:|---|
| Todas | Sin filas en cuarentena | 0 | |
