"""
Fuente 2 - IDEAM en datos.gov.co (Socrata, lenguaje de consulta SoQL).
Los datasets tienen millones de observaciones: se filtra y se agrega por dia en el
servidor, y se pagina con $limit / $offset.
Documentacion SoQL: https://dev.socrata.com/docs/queries/
"""
import sys

import pandas as pd

from src import config
from src.utils import guardar_bronce, http_json, log, ventanas, ya_existe

CAMPOS = "codigoestacion, nombreestacion, municipio, latitud, longitud"
PAGINA = 50000

# (nombre en bronce, url del dataset, columna de salida, funcion de agregacion diaria)
DATASETS = [
    ("ideam_precipitacion_diaria", config.IDEAM_URL, "precipitacion_mm", "sum"),
    ("ideam_temperatura_diaria", config.IDEAM_TEMPERATURA_URL, "temperatura_c", "avg"),
]


def consulta_soql(inicio, fin, offset: int, columna: str, agregacion: str) -> dict:
    """Parametros SoQL: filtra el departamento y las fechas, y agrega el valor por dia."""
    return {
        "$select": f"{CAMPOS}, date_trunc_ymd(fechaobservacion) AS fecha, "
                   f"{agregacion}(valorobservado) AS {columna}, count(*) AS n_obs",
        "$where": f"departamento = '{config.IDEAM_DEPARTAMENTO}' AND "
                  f"fechaobservacion BETWEEN '{inicio}T00:00:00' AND '{fin}T23:59:59'",
        "$group": f"{CAMPOS}, fecha",
        "$order": "fecha, codigoestacion",
        "$limit": PAGINA,
        "$offset": offset,
    }


def extraer_dataset(nombre: str, url: str, columna: str, agregacion: str, forzar: bool) -> None:
    if ya_existe(nombre, forzar):
        return
    if not url:
        raise RuntimeError(f"Falta la URL del dataset de {nombre} en src/config.py")
    filas = []
    for inicio, fin in ventanas(config.IDEAM_FECHA_INICIO, config.FECHA_FIN, config.IDEAM_DIAS_VENTANA):
        offset = 0
        while True:
            lote = http_json("GET", url, params=consulta_soql(inicio, fin, offset, columna, agregacion))
            filas.extend(lote)
            if len(lote) < PAGINA:
                break
            offset += PAGINA
        log(f"   {columna} semana {inicio} a {fin}: {len(lote)} filas")
    guardar_bronce(pd.DataFrame(filas), nombre, fuente="IDEAM", origen=url)


def extraer(forzar: bool = False) -> None:
    """Descarga la precipitacion y la temperatura diarias por estacion."""
    log("IDEAM - datos abiertos (SoQL)")
    for nombre, url, columna, agregacion in DATASETS:
        extraer_dataset(nombre, url, columna, agregacion, forzar)


if __name__ == "__main__":
    extraer(forzar="--forzar" in sys.argv)