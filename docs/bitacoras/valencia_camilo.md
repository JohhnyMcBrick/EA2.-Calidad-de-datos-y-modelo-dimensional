# Bitácora – Valencia, Camilo

Proyecto Integrado IV · EA2 Calidad de datos y modelo dimensional

| Fecha | Qué hice | Resultado |
|---|---|---|
| 26 oct 2026 | Revisé el código base de la clase y el Excel de EnerAndes (4 hojas). | Identifiqué los errores de cada hoja. |
| 11 nov 2026 | Corrí `python -m src.pipeline` y ajusté la descarga del catálogo de XM (`ListadoRecursos`), que daba error 400. | Quedó `xm_recursos` en bronce (2.512 filas). |
| 11 nov 2026 | Agregué la descarga de temperatura del IDEAM (dataset `sbwg-7ju4`) en `src/extract/ideam.py` y `config.py`. | `ideam_temperatura_diaria` en bronce (1.708 filas). |
| 11 nov 2026 | Corrí `python -m src.transformar`: limpieza de las 4 fuentes con pandera y `dbt build`. | Plata y oro construidas; `dbt build` 87 de 87. |
| 11 nov 2026 | Vi que la consulta 05 mostraba una sola planta. Encontré que XM entrega el código de la planta en la columna `code` y no en `Id`, y corregí `src/silver/xm.py`. Agregué una prueba. | La consulta 05 muestra 6 tipos de planta; pytest 39 de 39. |
| 11 nov 2026 | Pasé el entorno a Python 3.12. | Pruebas pasan en 3.12.10. |
| 11 nov 2026 | Actualicé el README con el resumen por fuente y los resultados de las consultas 04 y 05. | README completo. |