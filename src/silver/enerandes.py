"""
Capa plata: ventas de EnerAndes (las 4 hojas del Excel, 2023 a 2026) en una sola tabla.

Lee data/bronze/enerandes_ventas_<anio>.parquet, aplica las reglas de limpieza midiendo
cada problema antes y despues, valida con pandera y guarda en data/silver/:
  - enerandes_ventas.parquet       filas limpias
  - enerandes_cuarentena.parquet   filas que no se pueden corregir, con su motivo

Uso:
    python -m src.silver.enerandes
"""
import re
import unicodedata

import pandas as pd

from src import config
from src.quality import calidad
from src.quality.calidad import Medidor
from src.quality.esquemas import ESQUEMA_VENTAS
from src.utils import log

LINAJE = ["_fuente", "_origen", "_extraido_en"]
HOJAS = ["2023", "2024", "2025", "2026"]
FUENTE = "EnerAndes"

ENCABEZADOS = {
    "periodo": ["fecha", "periodo", "mes", "fecha corte"],
    "municipio": ["municipio", "ciudad"],
    "segmento": ["segmento", "segmento cliente", "tipo cliente"],
    "tipo_compra": ["tipo_compra", "tipo compra", "modalidad", "compra"],
    "energia": ["energia_kwh", "energia", "consumo (kwh)", "kwh"],
    "unidad": ["unidad"],
    "valor_cop": ["valor_cop", "valor ($)", "facturado", "total facturado cop"],
    "clientes": ["clientes", "num clientes", "usuarios", "clientes activos"],
}
NOMBRE_ESTANDAR = {alias: estandar for estandar, alias_lista in ENCABEZADOS.items() for alias in alias_lista}
MINIMO_ENCABEZADOS = 5

MUNICIPIOS = {
    "medellin": ("05001", "Medellín"),
    "santa fe de antioquia": ("05042", "Santa Fe de Antioquia"),
    "apartado": ("05045", "Apartadó"),
    "bello": ("05088", "Bello"),
    "caldas": ("05129", "Caldas"),
    "caucasia": ("05154", "Caucasia"),
    "copacabana": ("05212", "Copacabana"),
    "envigado": ("05266", "Envigado"),
    "girardota": ("05308", "Girardota"),
    "itagui": ("05360", "Itagüí"),
    "la estrella": ("05380", "La Estrella"),
    "marinilla": ("05440", "Marinilla"),
    "rionegro": ("05615", "Rionegro"),
    "sabaneta": ("05631", "Sabaneta"),
    "turbo": ("05837", "Turbo"),
}
ALIAS_MUNICIPIO = {
    "rio negro": "rionegro",
    "rionegro (ant)": "rionegro",
    "medellin d.e.": "medellin",
    "sta fe de antioquia": "santa fe de antioquia",
    "santafe de antioquia": "santa fe de antioquia",
}
SEGMENTOS = {"residencial": "Residencial", "resid.": "Residencial",
             "comercial": "Comercial", "industrial": "Industrial", "ind": "Industrial"}
TIPOS_COMPRA = {"bolsa": "Bolsa", "contrato": "Contrato", "contratos": "Contrato"}
FACTOR_UNIDAD = {"kwh": 1.0, "mwh": 1000.0}

MESES = {
    "ene": 1, "jan": 1, "feb": 2, "mar": 3, "abr": 4, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "aug": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12, "dec": 12,
}
FORMATOS_PERIODO = [
    ("AAAA-MM", re.compile(r"^(\d{4})-(\d{1,2})$")),
    ("mmm-aa", re.compile(r"^([a-z]{3})-(\d{2})$")),
    ("MM/AAAA", re.compile(r"^(\d{1,2})/(\d{4})$")),
    ("DD/MM/AAAA", re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")),
]
ORDEN = ["periodo", "divipola", "municipio", "segmento", "tipo_compra", "energia_kwh", "valor_cop", "clientes"]


def sin_tildes(texto: str) -> str:
    """'Itagüí' -> 'itagui': minuscula, sin espacios a los lados y sin tildes."""
    letras = unicodedata.normalize("NFD", str(texto).strip().lower())
    return "".join(c for c in letras if unicodedata.category(c) != "Mn")


def clave_municipio(texto) -> str | None:
    if pd.isna(texto):
        return None
    clave = sin_tildes(texto)
    return ALIAS_MUNICIPIO.get(clave, clave)


def formato_periodo(texto) -> str | None:
    """Nombre del formato en que viene un periodo, o None si no se reconoce."""
    if pd.isna(texto):
        return None
    limpio = sin_tildes(texto)
    for nombre, patron in FORMATOS_PERIODO:
        if patron.match(limpio):
            return nombre
    return None


def parsear_periodo(texto) -> str | None:
    """Convierte cualquiera de los 4 formatos de fecha al periodo 'AAAA-MM'."""
    formato = formato_periodo(texto)
    if formato is None:
        return None
    limpio = sin_tildes(texto)
    if formato == "AAAA-MM":
        anio, mes = (int(x) for x in limpio.split("-"))
    elif formato == "mmm-aa":
        abreviatura, anio_corto = limpio.split("-")
        if abreviatura not in MESES:
            return None
        mes, anio = MESES[abreviatura], 2000 + int(anio_corto)
    elif formato == "MM/AAAA":
        mes, anio = (int(x) for x in limpio.split("/"))
    else:
        _, mes, anio = (int(x) for x in limpio.split("/"))
    if not 1 <= mes <= 12:
        return None
    return f"{anio:04d}-{mes:02d}"


def ubicar_encabezado(bronce: pd.DataFrame) -> int:
    """Posicion de la fila que contiene los nombres de las columnas."""
    for posicion in range(min(len(bronce), 15)):
        reconocidos = sum(sin_tildes(c) in NOMBRE_ESTANDAR for c in bronce.iloc[posicion] if pd.notna(c))
        if reconocidos >= MINIMO_ENCABEZADOS:
            return posicion
    raise ValueError("No se encontro la fila de encabezados en las primeras 15 filas de la hoja")


def a_numero(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce")


def normalizar_hoja(bronce: pd.DataFrame, hoja: str, medidor: Medidor) -> pd.DataFrame:
    """Deja una hoja con columnas estandar, periodo AAAA-MM y energia en kWh."""
    df = bronce.drop(columns=LINAJE, errors="ignore")

    posicion = ubicar_encabezado(df)
    encabezado = [NOMBRE_ESTANDAR[sin_tildes(c)] if pd.notna(c) and sin_tildes(c) in NOMBRE_ESTANDAR else None
                  for c in df.iloc[posicion]]
    medidor.medir("Filas de título y notas antes del encabezado", "Ubicar la fila de encabezados y descartar lo anterior",
                  posicion, 0)
    df = df.iloc[posicion + 1:].copy()
    df.columns = [f"_{i}" if n is None else n for i, n in enumerate(encabezado)]
    df = df[[c for c in df.columns if not c.startswith("_")]]

    es_total = df["periodo"].astype("string").str.strip().str.upper().eq("TOTAL").fillna(False)
    medidor.medir("Filas de totales", "Eliminarlas", int(es_total.sum()), 0)
    df = df[~es_total].copy()
    df["hoja"] = hoja

    formatos = df["periodo"].map(formato_periodo)
    fuera_estandar = formatos.notna() & (formatos != "AAAA-MM")
    medidor.medir("Fechas en formatos distintos a AAAA-MM", "Convertir mmm-aa, MM/AAAA y DD/MM/AAAA a AAAA-MM",
                  int(fuera_estandar.sum()), 0)
    dia_mes_anio = formatos == "DD/MM/AAAA"
    medidor.medir("Fecha de corte día/mes/año (hoja 2026)", "Leer el segundo número como mes, no como día",
                  int(dia_mes_anio.sum()), 0)
    df["periodo"] = df["periodo"].map(parsear_periodo)

    if "unidad" in df.columns:
        unidad = df["unidad"].map(lambda u: sin_tildes(u) if pd.notna(u) else None)
    else:
        unidad = pd.Series("kwh", index=df.index)
    factor = unidad.map(FACTOR_UNIDAD)
    en_mwh = unidad == "mwh"
    medidor.medir("Energía en MWh mezclada con kWh", "Multiplicar por 1000 para dejar todo en kWh", int(en_mwh.sum()), 0)
    df["energia_kwh"] = (a_numero(df["energia"]) * factor).round(3)
    df["unidad_valida"] = factor.notna()
    for col in ["valor_cop", "clientes"]:
        df[col] = a_numero(df[col])
    columnas = ["periodo", "municipio", "segmento", "tipo_compra", "energia_kwh", "valor_cop", "clientes",
                "unidad_valida", "hoja"]
    return df[columnas]


def limpiar_valores(df: pd.DataFrame, medidor: Medidor) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Unifica categorias, quita duplicados y separa lo que no se puede corregir."""
    df = df.copy()

    antes = df["segmento"].nunique()
    df["segmento"] = df["segmento"].map(lambda s: SEGMENTOS.get(sin_tildes(s)) if pd.notna(s) else None)
    vacios = int(df["segmento"].isna().sum())
    df["segmento"] = df["segmento"].fillna("No informado")
    medidor.medir("Segmento escrito de varias formas", "Unificar a 3 valores", antes, df["segmento"].nunique() - 1)
    medidor.medir("Segmento vacío", "Marcarlo como 'No informado'", vacios, 0)

    antes = df["tipo_compra"].nunique()
    df["tipo_compra"] = df["tipo_compra"].map(lambda t: TIPOS_COMPRA.get(sin_tildes(t)) if pd.notna(t) else None)
    medidor.medir("Tipo de compra escrito de varias formas", "Unificar a Bolsa y Contrato", antes,
                  df["tipo_compra"].nunique())

    antes = df["municipio"].nunique()
    claves = df["municipio"].map(clave_municipio)
    df["divipola"] = claves.map(lambda c: MUNICIPIOS[c][0] if c in MUNICIPIOS else None)
    df["municipio"] = claves.map(lambda c: MUNICIPIOS[c][1] if c in MUNICIPIOS else None)
    medidor.medir("Municipio escrito de varias formas", "Unificar con el nombre oficial y el código DIVIPOLA",
                  antes, df["municipio"].nunique())

    columnas_clave = [c for c in df.columns if c not in ("hoja", "unidad_valida")]
    antes = int(df.duplicated(subset=columnas_clave).sum())
    df = df.drop_duplicates(subset=columnas_clave)
    medidor.medir("Filas duplicadas", "Dejar una sola copia", antes, int(df.duplicated(subset=columnas_clave).sum()))

    motivo = pd.Series(pd.NA, index=df.index, dtype="object")
    reglas = [
        ("Periodo no interpretable", df["periodo"].isna()),
        ("Municipio no reconocido", df["divipola"].isna()),
        ("Tipo de compra no reconocido", df["tipo_compra"].isna()),
        ("Unidad de energía desconocida", ~df["unidad_valida"]),
        ("Energía vacía", df["energia_kwh"].isna() & df["unidad_valida"]),
        ("Energía negativa", df["energia_kwh"] < 0),
        ("Valor facturado negativo", df["valor_cop"] < 0),
        ("Clientes vacío", df["clientes"].isna()),
        ("Clientes negativo", df["clientes"] < 0),
    ]
    conteos = {}
    for nombre, mascara in reglas:
        conteos[nombre] = int((mascara & motivo.isna()).sum())
        motivo = motivo.mask(mascara & motivo.isna(), nombre)

    medidor.medir("Energía vacía", "Pasar la fila a cuarentena", conteos["Energía vacía"], 0)
    medidor.medir("Energía negativa", "Pasar la fila a cuarentena", conteos["Energía negativa"], 0)
    medidor.medir("Valor facturado negativo", "Pasar la fila a cuarentena", conteos["Valor facturado negativo"], 0)
    medidor.medir("Clientes vacío o negativo", "Pasar la fila a cuarentena",
                  conteos["Clientes vacío"] + conteos["Clientes negativo"], 0)
    medidor.medir("Periodo, municipio, tipo de compra o unidad no reconocidos", "Pasar la fila a cuarentena",
                  conteos["Periodo no interpretable"] + conteos["Municipio no reconocido"]
                  + conteos["Tipo de compra no reconocido"] + conteos["Unidad de energía desconocida"], 0)

    cuarentena = df[motivo.notna()].assign(motivo=motivo[motivo.notna()])
    df = df[motivo.isna()].copy()
    vacios_valor = int(df["valor_cop"].isna().sum())
    medidor.medir("Valor facturado vacío", "Dejarlo vacío y documentarlo", vacios_valor, vacios_valor)

    df["clientes"] = df["clientes"].astype(int)
    df["energia_kwh"] = df["energia_kwh"].astype(float)
    return df[ORDEN].reset_index(drop=True), cuarentena.drop(columns=["unidad_valida"]).reset_index(drop=True)


def limpiar(bronce: pd.DataFrame, hoja: str = "2023") -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Limpia una sola hoja. Devuelve (limpias, cuarentena, metricas)."""
    medidor = Medidor()
    normalizada = normalizar_hoja(bronce, hoja, medidor)
    limpias, cuarentena = limpiar_valores(normalizada, medidor)
    return limpias, cuarentena, medidor.filas


def limpiar_todas(hojas: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Limpia las hojas y las une en una sola tabla."""
    medidor = Medidor()
    normalizadas = []
    encabezados = set()
    for hoja, bronce in hojas.items():
        sin_linaje = bronce.drop(columns=LINAJE, errors="ignore")
        fila = sin_linaje.iloc[ubicar_encabezado(sin_linaje)]
        encabezados.update(sin_tildes(c) for c in fila if pd.notna(c))
        normalizadas.append(normalizar_hoja(bronce, hoja, medidor))
    medidor.filas = calidad.combinar(medidor.filas)
    medidor.filas.insert(0, {"problema": "Nombres de columna distintos entre hojas",
                             "regla aplicada": "Mapear cada encabezado a un nombre estándar",
                             "antes": len(encabezados), "despues": len(ENCABEZADOS) - 1})
    limpias, cuarentena = limpiar_valores(pd.concat(normalizadas, ignore_index=True), medidor)
    return limpias, cuarentena, medidor.filas


def main() -> None:
    hojas = {}
    for hoja in HOJAS:
        hojas[hoja] = pd.read_parquet(config.DIR_BRONZE / f"enerandes_ventas_{hoja}.parquet")
    filas_bronce = sum(len(h) for h in hojas.values())
    log(f"Bronce: {filas_bronce:,} filas en {len(hojas)} hojas")

    limpias, cuarentena, metricas = limpiar_todas(hojas)
    ESQUEMA_VENTAS.validate(limpias, lazy=True)
    log("Validación con pandera: OK")

    config.DIR_SILVER.mkdir(parents=True, exist_ok=True)
    limpias.to_parquet(config.DIR_SILVER / "enerandes_ventas.parquet", index=False)
    cuarentena.to_parquet(config.DIR_SILVER / "enerandes_cuarentena.parquet", index=False)
    calidad.guardar(
        FUENTE,
        [{"tabla": "enerandes_ventas", "bronce": filas_bronce, "plata": len(limpias), "cuarentena": len(cuarentena)}],
        metricas,
        {"enerandes_ventas": cuarentena["motivo"].value_counts().to_dict()},
    )
    log(f"Plata: {len(limpias):,} filas limpias y {len(cuarentena)} en cuarentena")


if __name__ == "__main__":
    main()
