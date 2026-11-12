"""
Capa plata: datos de XM (precio de bolsa, demanda, generacion por planta, embalses, aportes y catalogo de plantas).

Las metricas por hora llegan en 24 columnas (Hour01 a Hour24): aqui pasan a una fila por fecha y hora,
con los valores como numeros. Cada tabla se valida con pandera antes de guardarse.

Uso:
    python -m src.silver.xm
"""
import re

import pandas as pd

from src import config
from src.quality import calidad
from src.quality.calidad import Medidor
from src.quality.esquemas import (
    ESQUEMA_XM_APORTES, ESQUEMA_XM_DEMANDA, ESQUEMA_XM_EMBALSES, ESQUEMA_XM_GENERACION,
    ESQUEMA_XM_PRECIO, ESQUEMA_XM_RECURSOS,
)
from src.utils import log

LINAJE = ["_fuente", "_origen", "_extraido_en"]
FUENTE = "XM"
COLUMNA_HORA = re.compile(r"^Hour(\d{2})$")

CAMPOS_RECURSO = {
    "code": "codigo_recurso", "name": "nombre_recurso", "type": "tipo_recurso",
    "state": "estado", "operstartdate": "fecha_operacion",
}


def a_numero(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce")


def a_fecha(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie, errors="coerce").dt.normalize()


def pasar_a_filas_por_hora(bronce: pd.DataFrame, columna_valor: str, columna_id: str | None = None) -> pd.DataFrame:
    """De Date, Id, Hour01..Hour24 a una fila por fecha y hora. Hour01 es la franja 00:00-01:00, hora 0."""
    horas = [c for c in bronce.columns if COLUMNA_HORA.match(c)]
    claves = ["Date"] + (["Id"] if columna_id else [])
    largo = bronce.melt(id_vars=claves, value_vars=horas, var_name="franja", value_name=columna_valor)
    largo["hora"] = largo["franja"].str[4:].astype(int) - 1
    largo = largo.rename(columns={"Date": "fecha", "Id": columna_id} if columna_id else {"Date": "fecha"})
    columnas = ["fecha", "hora"] + ([columna_id] if columna_id else []) + [columna_valor]
    return largo[columnas]


def separar(df: pd.DataFrame, motivos: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    return df[motivos.isna()].copy(), df[motivos.notna()].assign(motivo=motivos[motivos.notna()])


def asignar_motivos(df: pd.DataFrame, reglas: list[tuple[str, pd.Series]]) -> pd.Series:
    motivo = pd.Series(pd.NA, index=df.index, dtype="object")
    for nombre, mascara in reglas:
        motivo = motivo.mask(mascara & motivo.isna(), nombre)
    return motivo


def limpiar_serie_horaria(bronce: pd.DataFrame, tabla: str, columna_valor: str, maximo: float,
                          columna_id: str | None, medidor: Medidor):
    """Limpieza comun de precio, demanda y generacion: ancho a largo, numeros, nulos, rangos y duplicados."""
    datos = bronce.drop(columns=LINAJE, errors="ignore")
    if columna_id:
        # XM entrega el código de la planta en la columna "code" (o "Values_code"); "Id" no la identifica
        for nombre in datos.columns:
            if nombre.lower() in ("code", "values_code"):
                datos = datos.assign(Id=datos[nombre])
                break
    columnas_hora = [c for c in datos.columns if COLUMNA_HORA.match(c)]
    medidor.medir("Valores por hora en 24 columnas (Hour01 a Hour24)", "Pasar a una fila por fecha y hora",
                  len(columnas_hora), 1, tabla)

    largo = pasar_a_filas_por_hora(datos, columna_valor, columna_id)
    sucios = largo[columna_valor].notna() & a_numero(largo[columna_valor]).isna()
    texto_antes = calidad.contar_texto(largo[columna_valor])
    largo[columna_valor] = a_numero(largo[columna_valor])
    medidor.medir("Valores guardados como texto", "Convertir a número", texto_antes,
                  calidad.contar_texto(largo[columna_valor]), tabla)
    largo["fecha"] = a_fecha(largo["fecha"])
    if columna_id:
        largo[columna_id] = largo[columna_id].astype("string").str.strip().str.upper()

    clave = ["fecha", "hora"] + ([columna_id] if columna_id else [])
    antes = int(largo.duplicated(subset=clave).sum())
    largo = largo.drop_duplicates(subset=clave)
    medidor.medir("Filas duplicadas por fecha y hora", "Dejar una sola copia", antes,
                  int(largo.duplicated(subset=clave).sum()), tabla)

    valor = largo[columna_valor]
    motivos = asignar_motivos(largo, [
        ("Fecha no interpretable", largo["fecha"].isna()),
        ("Valor no numérico", sucios.reindex(largo.index, fill_value=False)),
        ("Valor vacío", valor.isna()),
        ("Valor negativo", valor < 0),
        ("Valor fuera de rango", valor > maximo),
    ])
    limpias, cuarentena = separar(largo, motivos)
    medidor.medir("Valores vacíos", "Pasar la fila a cuarentena", int((motivos == "Valor vacío").sum()), 0, tabla)
    medidor.medir("Valores negativos", "Pasar la fila a cuarentena", int((motivos == "Valor negativo").sum()), 0, tabla)
    medidor.medir("Valores fuera de rango físico", "Pasar la fila a cuarentena",
                  int((motivos == "Valor fuera de rango").sum()), 0, tabla)
    limpias["hora"] = limpias["hora"].astype(int)
    limpias[columna_valor] = limpias[columna_valor].astype(float)
    return limpias.reset_index(drop=True), cuarentena.reset_index(drop=True)


def limpiar_precio(bronce, medidor):
    return limpiar_serie_horaria(bronce, "xm_precio_bolsa", "precio_cop_kwh", 10000, None, medidor)


def limpiar_demanda(bronce, medidor):
    return limpiar_serie_horaria(bronce, "xm_demanda", "demanda_kwh", 30_000_000, None, medidor)


def limpiar_generacion(bronce, medidor):
    limpias, cuarentena = limpiar_serie_horaria(bronce, "xm_generacion", "generacion_kwh", 5_000_000,
                                                "codigo_recurso", medidor)
    return limpias, cuarentena


def limpiar_diaria(bronce: pd.DataFrame, tabla: str, columna_valor: str, factor: float, maximo: float,
                   medidor: Medidor):
    """Limpieza comun de las series diarias (embalses y aportes)."""
    datos = bronce.drop(columns=LINAJE, errors="ignore")
    texto_antes = calidad.contar_texto(datos["Value"])
    df = pd.DataFrame({"fecha": a_fecha(datos["Date"]), columna_valor: a_numero(datos["Value"]) * factor})
    medidor.medir("Valores guardados como texto", "Convertir a número", texto_antes,
                  calidad.contar_texto(df[columna_valor]), tabla)
    antes = int(df.duplicated(subset=["fecha"]).sum())
    df = df.drop_duplicates(subset=["fecha"])
    medidor.medir("Filas duplicadas por fecha", "Dejar una sola copia", antes, int(df.duplicated(subset=["fecha"]).sum()), tabla)
    motivos = asignar_motivos(df, [
        ("Fecha no interpretable", df["fecha"].isna()),
        ("Valor vacío", df[columna_valor].isna()),
        ("Valor negativo", df[columna_valor] < 0),
        ("Valor fuera de rango", df[columna_valor] > maximo),
    ])
    limpias, cuarentena = separar(df, motivos)
    medidor.medir("Valores vacíos, negativos o fuera de rango", "Pasar la fila a cuarentena", len(cuarentena), 0, tabla)
    return limpias.reset_index(drop=True), cuarentena.reset_index(drop=True)


def limpiar_embalses(bronce, medidor):
    return limpiar_diaria(bronce, "xm_embalses", "embalses_pct", 100.0, 100.0, medidor)


def limpiar_aportes(bronce, medidor):
    return limpiar_diaria(bronce, "xm_aportes", "aportes_kwh", 1.0, 1e12, medidor)


def limpiar_recursos(bronce: pd.DataFrame, medidor: Medidor):
    """Catalogo de plantas: nombres de columna estandar, texto sin espacios y una fila por codigo."""
    tabla = "xm_recursos"
    datos = bronce.drop(columns=LINAJE + ["Date"], errors="ignore")
    renombres = {}
    for columna in datos.columns:
        clave = re.sub(r"^values_", "", columna.strip().lower())
        if clave in CAMPOS_RECURSO:
            renombres[columna] = CAMPOS_RECURSO[clave]
    df = datos.rename(columns=renombres)[list(renombres.values())].copy()
    for opcional in ("estado", "fecha_operacion"):
        if opcional not in df.columns:
            df[opcional] = pd.NA
    medidor.medir("Nombres de columna del catálogo en inglés", "Renombrar a nombres estándar en español",
                  len(renombres), 0, tabla)

    for col in ["codigo_recurso", "nombre_recurso", "tipo_recurso"]:
        df[col] = df[col].astype("string").str.strip()
    df["codigo_recurso"] = df["codigo_recurso"].str.upper()
    df["tipo_recurso"] = df["tipo_recurso"].str.upper()
    if "fecha_operacion" in df.columns:
        df["fecha_operacion"] = pd.to_datetime(df["fecha_operacion"], errors="coerce")
    df["estado"] = df["estado"].astype("string").str.strip().str.upper()

    antes = int(df.duplicated(subset=["codigo_recurso"]).sum())
    df = df.drop_duplicates(subset=["codigo_recurso"])
    medidor.medir("Plantas repetidas en el catálogo", "Dejar una fila por código de recurso", antes,
                  int(df.duplicated(subset=["codigo_recurso"]).sum()), tabla)

    incompletas = df[["codigo_recurso", "nombre_recurso", "tipo_recurso"]].isna().any(axis=1) | (
        df["codigo_recurso"].fillna("") == "")
    medidor.medir("Plantas sin código, nombre o tipo", "Pasar la fila a cuarentena", int(incompletas.sum()), 0, tabla)
    cuarentena = df[incompletas].assign(motivo="Código, nombre o tipo vacío")
    df = df[~incompletas]
    for col in ["codigo_recurso", "nombre_recurso", "tipo_recurso", "estado"]:
        df[col] = df[col].astype(object)
    df["fecha_operacion"] = pd.to_datetime(df["fecha_operacion"], errors="coerce")
    return df.reset_index(drop=True), cuarentena.reset_index(drop=True)


PROCESOS = [
    ("xm_precio_bolsa", limpiar_precio, ESQUEMA_XM_PRECIO),
    ("xm_demanda", limpiar_demanda, ESQUEMA_XM_DEMANDA),
    ("xm_generacion", limpiar_generacion, ESQUEMA_XM_GENERACION),
    ("xm_embalses", limpiar_embalses, ESQUEMA_XM_EMBALSES),
    ("xm_aportes", limpiar_aportes, ESQUEMA_XM_APORTES),
    ("xm_recursos", limpiar_recursos, ESQUEMA_XM_RECURSOS),
]


def main() -> None:
    medidor = Medidor()
    tablas, motivos_cuarentena = [], {}
    config.DIR_SILVER.mkdir(parents=True, exist_ok=True)
    for nombre, limpiar, esquema in PROCESOS:
        bronce = pd.read_parquet(config.DIR_BRONZE / f"{nombre}.parquet")
        log(f"{nombre}: {len(bronce):,} filas en bronce")
        limpias, cuarentena = limpiar(bronce, medidor)
        esquema.validate(limpias, lazy=True)
        limpias.to_parquet(config.DIR_SILVER / f"{nombre}.parquet", index=False)
        cuarentena.to_parquet(config.DIR_SILVER / f"{nombre}_cuarentena.parquet", index=False)
        tablas.append({"tabla": nombre, "bronce": len(bronce), "plata": len(limpias), "cuarentena": len(cuarentena)})
        motivos_cuarentena[nombre] = cuarentena["motivo"].value_counts().to_dict() if len(cuarentena) else {}
        log(f"   plata: {len(limpias):,} filas, cuarentena: {len(cuarentena)}; validación con pandera: OK")
    calidad.guardar(FUENTE, tablas, medidor.filas, motivos_cuarentena)


if __name__ == "__main__":
    main()