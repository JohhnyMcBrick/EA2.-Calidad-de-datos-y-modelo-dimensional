"""Genera docs/reporte_calidad.md a partir de las metricas que guardo cada limpieza."""
from src import config
from src.quality import calidad

FUENTES = ["EnerAndes", "XM", "IDEAM", "NOAA", "FuentePropia"]

EXPLICACION_CUARENTENA = {
    "Energía vacía": "no hay cómo reconstruir el consumo de esa fila sin inventarlo",
    "Energía negativa": "un consumo negativo es un error de captura y no se sabe cuál era el valor real",
    "Valor facturado negativo": "un valor facturado negativo no es una venta",
    "Clientes vacío": "sin número de clientes la fila no se puede usar como medida",
    "Clientes negativo": "un número de clientes negativo es un error de captura",
    "Periodo no interpretable": "la fecha no coincide con ninguno de los formatos conocidos",
    "Municipio no reconocido": "el municipio no está en el catálogo DIVIPOLA del proyecto",
    "Tipo de compra no reconocido": "el tipo de compra no es Bolsa ni Contrato",
    "Unidad de energía desconocida": "la unidad no es kWh ni MWh",
    "Fecha no interpretable": "la fecha no se pudo convertir",
    "Valor no numérico": "el valor no se pudo convertir a número",
    "Valor vacío": "XM o el IDEAM no reportaron dato para esa franja",
    "Valor negativo": "la magnitud no puede ser negativa",
    "Valor fuera de rango": "supera el máximo físico razonable de la variable",
    "Código de sin dato": "el valor es el código de 'sin dato' del IDEAM, no una medición",
    "Estación sin municipio": "no hay otra fila de la estación que permita conocer su municipio",
    "Coordenadas vacías": "la estación no tiene latitud o longitud",
    "Número de observaciones inválido": "no se sabe cuántas mediciones respaldan el valor diario",
    "Código, nombre o tipo vacío": "la planta no se puede identificar",
    "Trimestre, año u ONI no válido": "el trimestre no se puede asignar a un mes",
}


def _tabla_metricas(metricas: list[dict]) -> list[str]:
    hay_tabla = any("tabla" in m for m in metricas)
    if hay_tabla:
        lineas = ["| # | Tabla | Problema | Regla aplicada | Antes | Después |", "|---|---|---|---|---:|---:|"]
    else:
        lineas = ["| # | Problema | Regla aplicada | Antes | Después |", "|---|---|---|---:|---:|"]
    for n, m in enumerate(metricas, start=1):
        celdas = [str(n)] + ([m.get("tabla", "")] if hay_tabla else []) + [
            m["problema"], m["regla aplicada"], str(m["antes"]), str(m["despues"])]
        lineas.append("| " + " | ".join(celdas) + " |")
    return lineas


def _seccion_cuarentena(contenido: dict) -> list[str]:
    lineas = ["", "Filas en cuarentena:", "", "| Tabla | Motivo | Filas | Por qué no se corrige |", "|---|---|---:|---|"]
    hay = False
    for tabla, motivos in contenido["cuarentena"].items():
        for motivo, n in motivos.items():
            hay = True
            lineas.append(f"| {tabla} | {motivo} | {n} | {EXPLICACION_CUARENTENA.get(motivo, '')} |")
    if not hay:
        lineas.append("| Todas | Sin filas en cuarentena | 0 | |")
    return lineas


def generar() -> int:
    """Escribe el reporte y devuelve el numero total de reglas medidas."""
    contenidos = [c for c in (calidad.leer(f) for f in FUENTES) if c]
    for c in contenidos:
        c["metricas"] = [m for m in c["metricas"] if m["antes"] > 0]
    total_reglas = sum(len(c["metricas"]) for c in contenidos)
    lineas = [
        "# Reporte de calidad de la capa plata",
        "",
        "Este archivo lo genera `python -m src.transformar` con las métricas que mide cada programa de limpieza. "
        "Cada regla muestra el problema, la regla aplicada y la métrica antes y después de corregirlo.",
        "",
        f"Reglas medidas en total: {total_reglas}. Las reglas que no encontraron casos en los datos no se listan.",
        "",
        "## Resumen por tabla",
        "",
        "| Fuente | Tabla | Filas en bronce | Filas en plata | Filas en cuarentena |",
        "|---|---|---:|---:|---:|",
    ]
    for c in contenidos:
        for t in c["tablas"]:
            lineas.append(f"| {c['fuente']} | {t['tabla']} | {t['bronce']:,} | {t['plata']:,} | {t['cuarentena']:,} |")
    if any(c["fuente"] == "XM" for c in contenidos):
        lineas += ["", "Las series horarias de XM llegan con una fila por día y 24 columnas de hora; en plata quedan con una "
                   "fila por hora, por eso tienen más filas que en bronce."]
    for c in contenidos:
        lineas += ["", f"## {c['fuente']}", ""] + _tabla_metricas(c["metricas"]) + _seccion_cuarentena(c)
    config.DIR_DOCS.mkdir(parents=True, exist_ok=True)
    (config.DIR_DOCS / "reporte_calidad.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return total_reglas


if __name__ == "__main__":
    print(f"Reporte escrito con {generar()} reglas")
