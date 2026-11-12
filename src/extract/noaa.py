"""
Fuente 3 - NOAA: indice ONI de El Nino (archivo de texto separado por espacios).
  Columnas: SEAS (trimestre movil, ej. JAS), YR (anio), TOTAL (temp. del mar), ANOM (anomalia)
  ANOM >= +0.5  -> El Nino      ANOM <= -0.5 -> La Nina
"""
# ---------------------------------------------------------------------------
# IMPORTS (traer codigo que ya existe)
# ---------------------------------------------------------------------------
# io: libreria de Python para entradas y salidas.
# io.StringIO hace que un texto en memoria se pueda leer como si fuera un archivo
import io

# pandas: la libreria de tablas. Aqui se usa read_csv para leer el texto como tabla
import pandas as pd

# config: el archivo src/config.py; de ahi sale la URL del archivo de NOAA
from src import config
# Funciones de src/utils.py:
#   guardar_bronce: guarda la tabla en Parquet con 3 columnas de linaje
#   http_texto:     descarga un archivo de texto de internet; reintenta si falla
#   log:            escribe un mensaje en pantalla con la hora
#   ya_existe:      dice si el archivo ya esta en bronce (para no descargarlo otra vez)
from src.utils import guardar_bronce, http_texto, log, ya_existe

# CONSTANTE (en mayusculas): el nombre del archivo en bronce -> data/bronze/noaa_oni.parquet
NOMBRE = "noaa_oni"


def extraer(forzar: bool = False) -> None:
    """Descarga el archivo del indice ONI y lo guarda en bronce."""
    # forzar: bool = False -> forzar es verdadero o falso; si no se indica, vale False.
    # -> None: la funcion no devuelve nada, solo trabaja
    # Avisa en pantalla que empieza con NOAA
    log("NOAA - indice ONI (El Nino)")
    # Si el archivo ya esta en bronce (y no se pidio forzar)...
    if ya_existe(NOMBRE, forzar):
        # ...return termina la funcion aqui, sin descargar
        return
    # Descarga el archivo .txt completo; texto queda con todo su contenido.
    # Empieza asi:  SEAS  YR   TOTAL   ANOM
    #                DJF  1950  24.72  -1.53
    texto = http_texto(config.NOAA_ONI_URL)
    # read_csv lee texto con columnas y lo convierte en tabla:
    #   io.StringIO(texto) -> presenta el texto como si fuera un archivo
    #   sep=r"\s+"         -> las columnas estan separadas por uno o mas espacios
    #   dtype=str          -> todo como texto: en bronce no se convierte nada
    df = pd.read_csv(io.StringIO(texto), sep=r"\s+", dtype=str)
    # Guarda la tabla en data/bronze/noaa_oni.parquet con las 3 columnas de linaje
    guardar_bronce(df, NOMBRE, fuente="NOAA", origen=config.NOAA_ONI_URL)


# ---------------------------------------------------------------------------
# Este bloque solo se ejecuta cuando se corre ESTE archivo directamente:
#     python -m src.extract.noaa
# Cuando otro archivo lo importa (como pipeline.py), este bloque NO se ejecuta.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # sys.argv: la lista de lo que se escribio en el comando
    import sys
    # "--forzar" in sys.argv es True si el comando trae --forzar
    extraer(forzar="--forzar" in sys.argv)
