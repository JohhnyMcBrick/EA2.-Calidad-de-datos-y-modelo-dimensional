"""
Utilidades comunes a todos los extractores:
  - log():            mensajes con hora
  - http_json() / http_texto(): peticiones con REINTENTOS y espera exponencial
  - ya_existe():      idempotencia (no volver a descargar lo que ya esta)
  - guardar_bronce(): guarda en Parquet agregando columnas de LINAJE
"""
# ---------------------------------------------------------------------------
# IMPORTS
# Primero las librerias que trae Python, luego las instaladas con pip,
# y al final los archivos de este mismo proyecto. Es la convencion de Python.
# ---------------------------------------------------------------------------
# time: libreria de Python para el tiempo. Se usa time.sleep(5) para esperar 5 segundos
import time
# datetime: para saber la fecha y hora actual (datetime.now())
# timedelta: una cantidad de dias, para sumarla a una fecha (fecha + timedelta(days=1))
# timezone: la zona horaria; timezone.utc es la hora universal
from datetime import datetime, timedelta, timezone

# pandas: la libreria de tablas. "as pd" le da el nombre corto pd
import pandas as pd
# requests: la libreria para pedir datos a internet (GET para traer, POST para enviar)
import requests

# config: el archivo src/config.py de este proyecto (rutas, tiempos de espera...)
from src import config


# ---------------------------------------------------------------------------
# MENSAJES EN PANTALLA
# ---------------------------------------------------------------------------
def log(mensaje: str) -> None:
    """Escribe un mensaje en pantalla con la hora delante: [21:30:32] mensaje."""
    # f"..." es un f-string: lo que va entre { } se reemplaza por su valor.
    # datetime.now() es la hora actual; :%H:%M:%S la escribe como 21:30:32.
    # flush=True obliga a mostrar el mensaje de inmediato, sin esperar.
    # Ejemplo: log("Bronce: 1,114 filas") muestra [21:30:32] Bronce: 1,114 filas
    print(f"[{datetime.now():%H:%M:%S}] {mensaje}", flush=True)


# ---------------------------------------------------------------------------
# DESCARGAS CON REINTENTOS
# ---------------------------------------------------------------------------
def _con_reintentos(funcion, descripcion: str):
    """Ejecuta funcion(); si falla, espera 2, 4, 8... segundos y reintenta."""
    # El guion bajo al inicio del nombre (_con_reintentos) indica que es de uso interno.
    # range(1, 5) da 1, 2, 3, 4: intento toma cada valor, hasta HTTP_REINTENTOS (4)
    for intento in range(1, config.HTTP_REINTENTOS + 1):
        # try: intenta lo de adentro; si sale un error, salta al except
        try:
            # Llama a la funcion de descarga; si funciona, return devuelve el
            # resultado y termina aqui (no hace mas intentos)
            return funcion()
        # Si la descarga fallo por la red o el servidor, el error queda en la variable error
        except requests.RequestException as error:
            # Si ya era el ultimo intento (el 4), no hay mas que hacer
            if intento == config.HTTP_REINTENTOS:
                # raise detiene el programa con un error que dice que se descargaba y por que fallo
                raise RuntimeError(f"Fallo definitivo en {descripcion}: {error}") from error
            # ** es potencia: 2**1 = 2, 2**2 = 4, 2**3 = 8 segundos.
            # Cada vez se espera mas, para darle tiempo al servidor de recuperarse
            espera = 2 ** intento
            # Avisa en pantalla que fallo y cuanto va a esperar.
            # type(error).__name__ es el nombre del error, por ejemplo ReadTimeout
            log(f"   ! intento {intento} fallo ({type(error).__name__}); reintento en {espera} s")
            # Espera esos segundos y el for vuelve a empezar con el siguiente intento
            time.sleep(espera)


def http_json(metodo: str, url: str, **kwargs):
    """GET o POST que devuelve JSON, con reintentos."""
    # **kwargs recibe parametros extra con nombre (json=..., params=...)
    # y los pasa tal cual a requests. Ejemplo: http_json("POST", url, json=cuerpo)
    # llamar() es una funcion dentro de la funcion: hace UNA descarga
    def llamar():
        # Envia el pedido (GET o POST) a la url; timeout: maximo de segundos de espera
        r = requests.request(metodo, url, timeout=config.HTTP_TIMEOUT, **kwargs)
        # Si el servidor respondio con error (404 no existe, 500 fallo del servidor...),
        # lo convierte en un error de Python, para que _con_reintentos lo vuelva a intentar
        r.raise_for_status()
        # La respuesta llega como texto JSON; .json() la convierte en diccionario o lista de Python
        return r.json()
    # Ejecuta llamar() con reintentos; el texto "POST https://..." sirve para el mensaje de error
    return _con_reintentos(llamar, f"{metodo} {url}")


def http_texto(url: str) -> str:
    """GET que devuelve texto plano, con reintentos."""
    # Funcion que hace UNA descarga de un archivo de texto
    def llamar():
        # Pide el archivo con GET
        r = requests.get(url, timeout=config.HTTP_TIMEOUT)
        # Si el servidor respondio con error, lo convierte en un error de Python
        r.raise_for_status()
        # Devuelve el contenido del archivo como texto
        return r.text
    # Ejecuta llamar() con reintentos
    return _con_reintentos(llamar, f"GET {url}")


# ---------------------------------------------------------------------------
# FECHAS EN BLOQUES
# ---------------------------------------------------------------------------
def ventanas(inicio, fin, dias: int):
    """Parte el rango [inicio, fin] en bloques de 'dias' dias."""
    # Ejemplo con dias=30: (1-ene, 30-ene), (31-ene, 1-mar), ... hasta fin.
    # a es el primer dia del bloque; empieza en la fecha de inicio
    a = inicio
    # Repite mientras el bloque empiece antes o en la fecha final
    while a <= fin:
        # b es el ultimo dia del bloque: a + 29 dias (si dias=30).
        # min(..., fin) toma el menor de los dos, para no pasarse de la fecha final
        b = min(a + timedelta(days=dias - 1), fin)
        # yield entrega este bloque (a, b) a quien lo pidio y la funcion queda en pausa;
        # cuando le piden el siguiente, sigue desde aqui
        yield a, b
        # El siguiente bloque empieza el dia despues de b
        a = b + timedelta(days=1)


# ---------------------------------------------------------------------------
# CAPA BRONCE
# ---------------------------------------------------------------------------
def ruta_bronce(nombre: str):
    """Ruta del archivo en bronce: data/bronze/<nombre>.parquet"""
    # Ejemplo: ruta_bronce("noaa_oni") -> C:\clases\observatorio-energia\data\bronze\noaa_oni.parquet
    return config.DIR_BRONZE / f"{nombre}.parquet"


def ya_existe(nombre: str, forzar: bool) -> bool:
    """Idempotencia: si el archivo ya esta y no se pide forzar, no se descarga."""
    # .exists() es True si el archivo esta en el disco.
    # "and not forzar": y NO se pidio volver a descargar (--forzar)
    if ruta_bronce(nombre).exists() and not forzar:
        # Avisa que lo salta
        log(f"   = {nombre}.parquet ya existe; se omite (use --forzar para repetir)")
        # True: quien llamo sabe que no tiene que descargar
        return True
    # False: el archivo no esta (o se pidio forzar): hay que descargar
    return False


def guardar_bronce(df: pd.DataFrame, nombre: str, fuente: str, origen: str) -> None:
    """Guarda TAL CUAL llego + 3 columnas de linaje. En bronce no se modifica nada."""
    # .copy() hace una copia de la tabla, para no modificar la original
    df = df.copy()
    # Agrega la columna _fuente con el mismo valor en todas las filas: de donde vino ("XM")
    df["_fuente"] = fuente
    # Agrega la columna _origen: la URL o el archivo exacto de donde salio
    df["_origen"] = origen
    # Agrega la columna _extraido_en: la fecha y hora de la descarga, en hora universal (UTC).
    # .isoformat(timespec="seconds") la escribe asi: 2026-10-19T19:45:42+00:00
    df["_extraido_en"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # Crea la carpeta data/bronze si no existe.
    # parents=True crea tambien data/ si falta; exist_ok=True no da error si ya existe
    config.DIR_BRONZE.mkdir(parents=True, exist_ok=True)
    # Guarda la tabla en un archivo Parquet; index=False: sin la columna de numeros de fila
    df.to_parquet(ruta_bronce(nombre), index=False)
    # Avisa cuantas filas y columnas guardo.
    # len(df) = filas; df.shape[1] = columnas; :, pone separador de miles (1,114)
    log(f"   + {nombre}.parquet guardado: {len(df):,} filas x {df.shape[1]} columnas")
