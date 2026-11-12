"""
Punto de entrada del pipeline de extraccion (capa bronce).

Uso:
    python -m src.pipeline              # descarga lo que falte
    python -m src.pipeline --forzar     # vuelve a descargar todo
"""
import sys
import time

import pandas as pd

from src import config
from src.extract import enerandes, ideam, noaa, xm
from src.utils import log

EXTRACTORES = (("XM", xm), ("IDEAM", ideam), ("NOAA", noaa), ("EnerAndes", enerandes))


def resumen() -> None:
    """Muestra una tabla con los archivos de la capa bronce."""
    log("Resumen de la capa bronce:")
    print(f"   {'archivo':<34}{'filas':>10}{'columnas':>10}{'KB':>8}")
    for archivo in sorted(config.DIR_BRONZE.glob("*.parquet")):
        df = pd.read_parquet(archivo)
        print(f"   {archivo.name:<34}{len(df):>10,}{df.shape[1]:>10}{archivo.stat().st_size // 1024:>8}")


def main() -> None:
    forzar = "--forzar" in sys.argv
    inicio = time.time()
    log(f"Pipeline bronce | rango {config.FECHA_INICIO} a {config.FECHA_FIN} | forzar={forzar}")
    fallos = []
    for nombre, extractor in EXTRACTORES:
        try:
            extractor.extraer(forzar)
        except Exception as error:
            fallos.append((nombre, error))
            log(f"   !! {nombre} fallo: {str(error)[:200]}")
    resumen()
    if fallos:
        for nombre, error in fallos:
            log(f"FALLO {nombre}: {str(error)[:200]}")
        raise SystemExit("Fallaron fuentes: corrige y vuelve a correr (solo descarga lo que falta)")
    log(f"Listo en {time.time() - inicio:.0f} s")


if __name__ == "__main__":
    main()