"""
Fuente 4 - Archivo interno de EnerAndes (Excel con una hoja por anio).
  Cada hoja tiene encabezados DISTINTOS y algunas traen un titulo encima.
  Regla de bronce: NO se modifica. Guardamos cada hoja tal cual, como texto,
  incluidas las filas de titulo y la fila TOTAL. Limpiar es trabajo de la capa plata.
"""
# ---------------------------------------------------------------------------
# IMPORTS (traer codigo que ya existe)
# ---------------------------------------------------------------------------
# pandas: la libreria de tablas. "as pd" le da el nombre corto pd.
# Aqui se usa pd.read_excel para leer el Excel (por debajo usa openpyxl)
import pandas as pd

# config: el archivo src/config.py; de ahi sale la ruta del Excel (data/insumos/...)
from src import config
# Funciones de src/utils.py:
#   guardar_bronce: guarda la tabla en Parquet con 3 columnas de linaje
#   log:            escribe un mensaje en pantalla con la hora
#   ya_existe:      dice si el archivo ya esta en bronce (para no repetir el trabajo)
from src.utils import guardar_bronce, log, ya_existe


def extraer(forzar: bool = False) -> None:
    """Lee las 4 hojas del Excel de EnerAndes y guarda cada una en bronce."""
    # forzar: bool = False -> forzar es verdadero o falso; si no se indica, vale False
    # (no se repite el trabajo). -> None: la funcion no devuelve nada, solo trabaja
    # Avisa en pantalla que empieza con EnerAndes
    log("EnerAndes - Excel interno")
    # La ruta completa del Excel, tomada de config.py
    archivo = config.ENERANDES_EXCEL
    # .exists() es True si el archivo esta en el disco; "not" lo invierte:
    # entra al if cuando el Excel NO esta
    if not archivo.exists():
        # raise detiene el programa con un error y un mensaje que dice que hacer
        raise FileNotFoundError(f"No se encontro {archivo}. Copielo en data/insumos/.")

    # Lee el Excel:
    #   sheet_name=None -> lee TODAS las hojas y devuelve un diccionario {nombre de hoja: tabla}
    #                      Ejemplo: {"Ventas 2023": tabla, "Ventas 2024": tabla, ...}
    #   header=None     -> no toma ninguna fila como encabezado: deja todo tal cual
    #   dtype=str       -> todo como texto, sin convertir numeros ni fechas
    hojas = pd.read_excel(archivo, sheet_name=None, header=None, dtype=str)
    # .items() recorre el diccionario: en cada vuelta, nombre_hoja es el nombre
    # ("Ventas 2023") y df es la tabla de esa hoja
    for nombre_hoja, df in hojas.items():
        # Arma el nombre del archivo en bronce:
        # .lower() pasa a minuscula y .replace(" ", "_") cambia los espacios por guion bajo
        # "Ventas 2024" -> "ventas_2024" -> "enerandes_ventas_2024"
        nombre = "enerandes_" + nombre_hoja.lower().replace(" ", "_")
        # Si el archivo ya esta en bronce (y no se pidio forzar)...
        if ya_existe(nombre, forzar):
            # ...continue salta a la siguiente hoja, sin guardar esta otra vez
            continue
        # Como no hay encabezado, pandas nombra las columnas 0, 1, 2...
        # Parquet exige nombres de texto: se cambian por col_0, col_1, col_2...
        # df.shape[1] es el numero de columnas de la hoja; range() cuenta de 0 a ese numero
        df.columns = [f"col_{i}" for i in range(df.shape[1])]
        # Guarda la hoja en data/bronze/<nombre>.parquet con las 3 columnas de linaje.
        # origen queda como "ventas_enerandes_2023_2026.xlsx#Ventas 2023": archivo#hoja
        guardar_bronce(df, nombre, fuente="EnerAndes", origen=f"{archivo.name}#{nombre_hoja}")


# ---------------------------------------------------------------------------
# Este bloque solo se ejecuta cuando se corre ESTE archivo directamente:
#     python -m src.extract.enerandes
# Cuando otro archivo lo importa (como pipeline.py), este bloque NO se ejecuta.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # sys.argv: la lista de lo que se escribio en el comando
    import sys
    # "--forzar" in sys.argv es True si el comando trae --forzar
    extraer(forzar="--forzar" in sys.argv)
