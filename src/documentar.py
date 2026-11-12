"""
Genera docs/diccionario_datos.md: una tabla por cada tabla de la capa oro.

Los tipos de dato se leen de data/observatorio.duckdb; las descripciones y el origen de cada columna
se definen aqui, junto al modelo dbt que las produce.

Uso:
    python -m src.documentar
"""
import duckdb

from src import config

TABLAS = {
    "dim_fecha": ("Un día. Calendario del proyecto con la fase ENSO del mes.", {
        "fecha_id": ("Llave del día en formato AAAAMMDD.", "Calculada en dbt/models/marts/dim_fecha.sql"),
        "fecha": ("Fecha del día.", "Serie de días entre las variables fecha_inicio y fecha_fin de dbt_project.yml"),
        "mes_id": ("Llave del mes en formato AAAAMM.", "Calculada a partir de la fecha"),
        "anio": ("Año de la fecha.", "Calculada a partir de la fecha"),
        "mes": ("Número del mes, de 1 a 12.", "Calculada a partir de la fecha"),
        "nombre_mes": ("Nombre del mes en español.", "Calculada a partir de la fecha"),
        "trimestre": ("Trimestre del año, de 1 a 4.", "Calculada a partir de la fecha"),
        "dia_del_mes": ("Día del mes.", "Calculada a partir de la fecha"),
        "dia_semana": ("Día de la semana, de 1 (lunes) a 7 (domingo).", "Calculada a partir de la fecha"),
        "nombre_dia": ("Nombre del día de la semana en español.", "Calculada a partir de la fecha"),
        "es_fin_de_semana": ("Verdadero si el día es sábado o domingo.", "Calculada a partir de la fecha"),
        "oni": ("Índice ONI del mes. Vacío si NOAA aún no lo publica.", "silver/noaa_oni.parquet, columna oni"),
        "fase_enso": ("El Niño, La Niña, Neutral o Sin dato.", "silver/noaa_oni.parquet, columna fase_enso"),
    }),
    "dim_mes": ("Un mes. Se obtiene de dim_fecha.", {
        "mes_id": ("Llave del mes en formato AAAAMM.", "dim_fecha.mes_id"),
        "periodo": ("Mes en formato AAAA-MM.", "dim_fecha.fecha"),
        "anio": ("Año del mes.", "dim_fecha.anio"),
        "mes": ("Número del mes, de 1 a 12.", "dim_fecha.mes"),
        "nombre_mes": ("Nombre del mes en español.", "dim_fecha.nombre_mes"),
        "trimestre": ("Trimestre del año.", "dim_fecha.trimestre"),
        "oni": ("Índice ONI del mes.", "dim_fecha.oni"),
        "fase_enso": ("Fase del fenómeno en el mes.", "dim_fecha.fase_enso"),
    }),
    "dim_municipio": ("Un municipio de Antioquia con su código DIVIPOLA.", {
        "municipio_id": ("Código DIVIPOLA de 5 dígitos.", "silver/enerandes_ventas.parquet, columna divipola"),
        "municipio": ("Nombre oficial del municipio.", "silver/enerandes_ventas.parquet, columna municipio"),
        "departamento": ("Departamento del municipio.", "Constante: Antioquia"),
    }),
    "dim_segmento": ("Un segmento de cliente.", {
        "segmento_id": ("Número del segmento, asignado en orden alfabético.", "Calculada en dbt"),
        "segmento": ("Residencial, Comercial, Industrial o No informado.", "silver/enerandes_ventas.parquet, columna segmento"),
    }),
    "dim_recurso": ("Una planta de generación.", {
        "recurso_id": ("Código SIC de la planta.", "silver/xm_recursos.parquet, columna codigo_recurso"),
        "nombre_recurso": ("Nombre de la planta.", "silver/xm_recursos.parquet, columna nombre_recurso"),
        "tipo_recurso": ("Tipo de planta: hidráulica, térmica, eólica, solar u otro.", "silver/xm_recursos.parquet, columna tipo_recurso"),
        "estado": ("Estado operativo de la planta.", "silver/xm_recursos.parquet, columna estado"),
        "fecha_operacion": ("Fecha de inicio de operación.", "silver/xm_recursos.parquet, columna fecha_operacion"),
        "en_catalogo": ("Falso si la planta genera pero no está en ListadoRecursos.", "Calculada en dbt"),
    }),
    "dim_estacion": ("Una estación meteorológica del IDEAM.", {
        "estacion_id": ("Código de la estación.", "silver/ideam_precipitacion.parquet, columna codigo_estacion"),
        "estacion": ("Nombre de la estación.", "silver/ideam_precipitacion.parquet, columna estacion"),
        "municipio": ("Municipio donde está la estación.", "silver/ideam_precipitacion.parquet, columna municipio"),
        "latitud": ("Latitud en grados decimales.", "silver/ideam_precipitacion.parquet, columna latitud"),
        "longitud": ("Longitud en grados decimales.", "silver/ideam_precipitacion.parquet, columna longitud"),
    }),
    "fact_ventas_mensual": ("Grano: un mes, un municipio, un segmento y un tipo de compra.", {
        "mes_id": ("Llave a dim_mes.", "silver/enerandes_ventas.parquet, columna periodo"),
        "municipio_id": ("Llave a dim_municipio.", "silver/enerandes_ventas.parquet, columna divipola"),
        "segmento_id": ("Llave a dim_segmento.", "dim_segmento.segmento_id"),
        "tipo_compra": ("Bolsa o Contrato.", "silver/enerandes_ventas.parquet, columna tipo_compra"),
        "energia_kwh": ("Energía vendida en kWh.", "silver/enerandes_ventas.parquet, columna energia_kwh"),
        "valor_cop": ("Valor facturado en pesos. Puede estar vacío.", "silver/enerandes_ventas.parquet, columna valor_cop"),
        "clientes": ("Número de clientes del mes.", "silver/enerandes_ventas.parquet, columna clientes"),
    }),
    "fact_mercado_horario": ("Grano: una hora de un día en el sistema interconectado nacional.", {
        "mercado_hora_id": ("Llave de la hora: AAAAMMDD por 100 más la hora.", "Calculada en dbt"),
        "fecha_id": ("Llave a dim_fecha.", "silver/xm_precio_bolsa.parquet, columna fecha"),
        "hora": ("Hora de inicio de la franja, de 0 a 23.", "silver/xm_precio_bolsa.parquet, columna hora"),
        "precio_bolsa_cop_kwh": ("Precio de bolsa nacional en pesos por kWh.", "silver/xm_precio_bolsa.parquet, columna precio_cop_kwh"),
        "demanda_kwh": ("Demanda real del sistema en kWh.", "silver/xm_demanda.parquet, columna demanda_kwh"),
    }),
    "fact_generacion_recurso": ("Grano: una planta en una hora de un día.", {
        "generacion_id": ("Llave: fecha, hora y código de la planta.", "Calculada en dbt"),
        "fecha_id": ("Llave a dim_fecha.", "silver/xm_generacion.parquet, columna fecha"),
        "hora": ("Hora de inicio de la franja, de 0 a 23.", "silver/xm_generacion.parquet, columna hora"),
        "recurso_id": ("Llave a dim_recurso.", "silver/xm_generacion.parquet, columna codigo_recurso"),
        "generacion_kwh": ("Generación de la planta en kWh.", "silver/xm_generacion.parquet, columna generacion_kwh"),
    }),
    "fact_hidrologia_diaria": ("Grano: un día.", {
        "fecha_id": ("Llave a dim_fecha.", "silver/xm_embalses.parquet, columna fecha"),
        "embalses_pct": ("Porcentaje de volumen útil de los embalses.", "silver/xm_embalses.parquet, columna embalses_pct"),
        "aportes_kwh": ("Aportes hídricos de energía en kWh.", "silver/xm_aportes.parquet, columna aportes_kwh"),
    }),
    "fact_clima_diario": ("Grano: una estación del IDEAM en un día.", {
        "clima_id": ("Llave: fecha y código de la estación.", "Calculada en dbt"),
        "fecha_id": ("Llave a dim_fecha.", "silver/ideam_precipitacion.parquet, columna fecha"),
        "estacion_id": ("Llave a dim_estacion.", "silver/ideam_precipitacion.parquet, columna codigo_estacion"),
        "precipitacion_mm": ("Precipitación del día en milímetros.", "silver/ideam_precipitacion.parquet, columna precipitacion_mm"),
        "temperatura_c": ("Temperatura del día en grados Celsius.", "silver/ideam_temperatura.parquet, columna temperatura_c"),
    }),
}


def main() -> None:
    con = duckdb.connect(str(config.RAIZ / "data" / "observatorio.duckdb"), read_only=True)
    lineas = [
        "# Diccionario de datos de la capa oro",
        "",
        "Una tabla por cada tabla del esquema estrella. Los tipos de dato se leen de `data/observatorio.duckdb`; "
        "este archivo se genera con `python -m src.documentar`.",
    ]
    for tabla, (descripcion, columnas) in TABLAS.items():
        tipos = dict(con.execute(
            "select column_name, data_type from information_schema.columns where table_name = ? order by ordinal_position",
            [tabla]).fetchall())
        faltan = set(tipos) ^ set(columnas)
        if faltan:
            raise ValueError(f"{tabla}: el diccionario y la tabla no coinciden en {sorted(faltan)}")
        lineas += ["", f"## {tabla}", "", descripcion, "", "| Columna | Tipo de dato | Descripción | Origen |", "|---|---|---|---|"]
        for columna in tipos:
            descripcion_columna, origen = columnas[columna]
            lineas.append(f"| {columna} | {tipos[columna]} | {descripcion_columna} | {origen} |")
    config.DIR_DOCS.mkdir(parents=True, exist_ok=True)
    (config.DIR_DOCS / "diccionario_datos.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
