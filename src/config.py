"""
Configuracion central del pipeline.
Todo lo que puede cambiar (fechas, URLs, rutas) vive AQUI y no regado en el codigo.
Si hay que cambiar una fecha o una URL, se cambia en este archivo y en ningun otro.
"""
# ---------------------------------------------------------------------------
# IMPORTS (traer codigo que ya existe)
# ---------------------------------------------------------------------------
# datetime es la libreria de Python para fechas y horas.
# De ella se trae date, que sirve para escribir una fecha: date(2026, 1, 1) = 1 de enero de 2026
from datetime import date
# pathlib es la libreria de Python para manejar rutas de carpetas y archivos.
# De ella se trae Path: con Path las rutas funcionan igual en Windows (\) y en Mac o Linux (/)
from pathlib import Path

# ---------------------------------------------------------------------------
# RANGO DE FECHAS A EXTRAER
# ---------------------------------------------------------------------------
# Para la clase usamos 2026 (rapido). Para el proyecto, amplien a 2023-01-01.
# Primer dia que se descarga de las fuentes: 1 de enero de 2026
FECHA_INICIO = date(2026, 1, 1)
# Ultimo dia que se descarga: 30 de septiembre de 2026
FECHA_FIN = date(2026, 9, 30)

# ---------------------------------------------------------------------------
# RUTAS (las carpetas del proyecto)
# ---------------------------------------------------------------------------
# __file__ es la ruta de ESTE archivo: C:\clases\observatorio-energia\src\config.py
# .resolve() la vuelve una ruta completa.
# .parent sube una carpeta: la primera vez queda en ...\src; la segunda, en la raiz:
# RAIZ = C:\clases\observatorio-energia. Asi las rutas sirven en cualquier computador
RAIZ = Path(__file__).resolve().parent.parent
# El / une partes de una ruta (aqui no divide).
# DIR_INSUMOS = C:\clases\observatorio-energia\data\insumos: donde esta el Excel de EnerAndes
DIR_INSUMOS = RAIZ / "data" / "insumos"
# DIR_BRONZE = ...\data\bronze: donde se guardan los datos descargados, tal cual llegan
DIR_BRONZE = RAIZ / "data" / "bronze"
# DIR_SILVER = ...\data\silver: donde se guardan los datos ya limpios (capa plata)
DIR_SILVER = RAIZ / "data" / "silver"
# DIR_DOCS = ...\docs: donde se escriben el perfilamiento y el reporte de calidad
DIR_DOCS = RAIZ / "docs"

# ---------------------------------------------------------------------------
# FUENTE 1: API DE XM (mercado electrico)
# ---------------------------------------------------------------------------
# La direccion de la API. {periodo} es un hueco que despues se llena con
# hourly (por hora), daily (por dia) o lists (listas)
XM_URL = "https://servapibi.xm.com.co/{periodo}"
# La API de XM no acepta pedidos de mas de 30 dias: se piden de a 30 dias
XM_MAX_DIAS = 30
# Las metricas que se descargan de XM. Es una lista; cada elemento es una tupla
# (varios valores entre parentesis) con 4 datos:
# (codigo de la metrica en XM, entidad, periodo, nombre del archivo en bronce)
XM_METRICAS = [
    # Precio de bolsa de todo el pais, por hora -> data/bronze/xm_precio_bolsa.parquet
    ("PrecBolsNaci", "Sistema", "hourly", "xm_precio_bolsa"),
    # Demanda real de energia, por hora -> data/bronze/xm_demanda.parquet
    ("DemaReal", "Sistema", "hourly", "xm_demanda"),
    # Porcentaje de llenado de los embalses, por dia -> data/bronze/xm_embalses.parquet
    ("PorcVoluUtilDiar", "Sistema", "daily", "xm_embalses"),
    # Aportes hidricos de energia al sistema, por dia -> data/bronze/xm_aportes.parquet
    ("AporEner", "Sistema", "daily", "xm_aportes"),
    # Generacion real de cada planta, por hora -> data/bronze/xm_generacion.parquet
    ("Gene", "Recurso", "hourly", "xm_generacion"),
]

# Catalogos de XM (endpoint /lists): (codigo de la metrica, entidad, nombre del archivo en bronce)
XM_LISTAS = [
    ("ListadoRecursos", "Recurso", "xm_recursos"),
]

# ---------------------------------------------------------------------------
# FUENTE 2: IDEAM en datos.gov.co (lluvia)
# ---------------------------------------------------------------------------
# La direccion del conjunto de datos de precipitacion del IDEAM en datos.gov.co
IDEAM_URL = "https://www.datos.gov.co/resource/s54a-sgyg.json"
IDEAM_TEMPERATURA_URL = "https://www.datos.gov.co/resource/sbwg-7ju4.json"
# Solo se piden las estaciones de este departamento
IDEAM_DEPARTAMENTO = "ANTIOQUIA"
# Se pide de a 7 dias: si se pide mas, el servidor tarda tanto que corta la conexion
IDEAM_DIAS_VENTANA = 7
# El IDEAM es la fuente MAS LENTA (5 a 30 s por semana). Para la clase pedimos
# solo jun-sep 2026. Para el proyecto, usen el mismo rango de las demas fuentes.
# Primer dia que se pide al IDEAM: 1 de junio de 2026
IDEAM_FECHA_INICIO = date(2026, 6, 1)

# ---------------------------------------------------------------------------
# FUENTE 3: NOAA, indice de El Nino
# ---------------------------------------------------------------------------
# La direccion del archivo de texto con el indice ONI (El Nino y La Nina)
NOAA_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

# ---------------------------------------------------------------------------
# FUENTE 4: archivo interno de EnerAndes (Excel)
# ---------------------------------------------------------------------------
# La ruta completa del Excel: ...\data\insumos\ventas_enerandes_2023_2026.xlsx
ENERANDES_EXCEL = DIR_INSUMOS / "ventas_enerandes_2023_2026.xlsx"

# ---------------------------------------------------------------------------
# COMPORTAMIENTO DE LAS DESCARGAS
# ---------------------------------------------------------------------------
# Cuantos segundos se espera la respuesta de un servidor antes de darlo por perdido
HTTP_TIMEOUT = 120
# Cuantas veces se intenta una descarga si falla la red o el servidor
HTTP_REINTENTOS = 4
