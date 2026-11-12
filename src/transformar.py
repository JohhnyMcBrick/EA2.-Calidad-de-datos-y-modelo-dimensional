"""
Construye las capas plata y oro con un solo comando.

    python -m src.transformar

Ejecuta la limpieza de todas las fuentes (capa plata), escribe el reporte de calidad y
luego corre dbt build para crear el esquema estrella (capa oro) y regenera el diccionario de datos.
"""
import subprocess
import sys
import time

from src import config
from src import documentar
from src.quality import reporte
from src.silver import enerandes, ideam, noaa, xm
from src.utils import log

PROGRAMAS_PLATA = [("EnerAndes", enerandes), ("XM", xm), ("IDEAM", ideam), ("NOAA", noaa)]


def construir_plata() -> None:
    for nombre, modulo in PROGRAMAS_PLATA:
        log(f"Plata: {nombre}")
        modulo.main()
    reglas = reporte.generar()
    log(f"Reporte de calidad: docs/reporte_calidad.md ({reglas} reglas)")


def construir_oro() -> None:
    log("Oro: dbt build")
    comando = [sys.executable, "-m", "dbt.cli.main", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"]
    resultado = subprocess.run(comando, cwd=config.RAIZ)
    if resultado.returncode != 0:
        raise SystemExit(f"dbt build terminó con errores (código {resultado.returncode})")
    documentar.main()
    log("Diccionario de datos: docs/diccionario_datos.md")


def main() -> None:
    inicio = time.time()
    construir_plata()
    construir_oro()
    log(f"Capas plata y oro listas en {time.time() - inicio:.0f} s")


if __name__ == "__main__":
    main()
