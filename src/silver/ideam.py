"""
Capa plata: IDEAM (precipitacion y temperatura diarias por estacion).

Deja la fecha como fecha, los valores como numeros y cada estacion con su municipio.
Lee data/bronze/ideam_precipitacion_diaria.parquet y data/bronze/ideam_temperatura_diaria.parquet.

Uso:
    python -m src.silver.ideam
"""
import unicodedata

import pandas as pd

from src import config
from src.quality import calidad
from src.quality.calidad import Medidor
from src.quality.esquemas import ESQUEMA_IDEAM_PRECIPITACION, ESQUEMA_IDEAM_TEMPERATURA
from src.utils import log

LINAJE = ["_fuente", "_origen", "_extraido_en"]
FUENTE = "IDEAM"
CODIGOS_SIN_DATO = [-999, -9999, 999, 9999]


def sin_tildes_mayusculas(texto) -> str | None:
    if pd.isna(texto):
        return None
    letras = unicodedata.normalize("NFD", str(texto).strip().upper())
    texto = "".join(c for c in letras if unicodedata.category(c) != "Mn")
    return " ".join(texto.split()) or None


def completar_municipio(df: pd.DataFrame) -> pd.DataFrame:
    """Una estacion pertenece a un solo municipio: rellena los vacios con el que ya conocemos de esa estacion."""
    conocido = (df.dropna(subset=["municipio"]).groupby("codigo_estacion")["municipio"]
                .agg(lambda s: s.mode().iloc[0]))
    df = df.copy()
    df["municipio"] = df["municipio"].fillna(df["codigo_estacion"].map(conocido))
    return df


def limpiar_estacion(bronce: pd.DataFrame, tabla: str, columna_origen: str, columna_valor: str,
                     minimo: float, maximo: float, medidor: Medidor):
    datos = bronce.drop(columns=LINAJE, errors="ignore")
    texto_fecha = calidad.contar_texto(datos["fecha"])
    texto_valor = calidad.contar_texto(datos[columna_origen])
    df = pd.DataFrame({
        "fecha": pd.to_datetime(datos["fecha"], errors="coerce").dt.normalize(),
        "codigo_estacion": datos["codigoestacion"].astype("string").str.strip().str.lstrip("0"),
        "estacion": datos["nombreestacion"].map(sin_tildes_mayusculas),
        "municipio": datos["municipio"].map(sin_tildes_mayusculas),
        "latitud": pd.to_numeric(datos["latitud"], errors="coerce"),
        "longitud": pd.to_numeric(datos["longitud"], errors="coerce"),
        columna_valor: pd.to_numeric(datos[columna_origen], errors="coerce"),
        "n_obs": pd.to_numeric(datos.get("n_obs"), errors="coerce"),
    })
    medidor.medir("Fechas guardadas como texto con hora", "Convertir a fecha", texto_fecha, calidad.contar_texto(df["fecha"]), tabla)
    medidor.medir("Valores guardados como texto", "Convertir a número", texto_valor, calidad.contar_texto(df[columna_valor]), tabla)

    sin_dato = df[columna_valor].isin(CODIGOS_SIN_DATO)

    sin_municipio = int(df["municipio"].isna().sum())
    df = completar_municipio(df)
    medidor.medir("Filas de estación sin municipio", "Completar con el municipio conocido de la misma estación",
                  sin_municipio, int(df["municipio"].isna().sum()), tabla)

    antes = int(df.duplicated(subset=["fecha", "codigo_estacion"]).sum())
    df = df.drop_duplicates(subset=["fecha", "codigo_estacion"])
    medidor.medir("Filas duplicadas por estación y fecha", "Dejar una sola copia", antes,
                  int(df.duplicated(subset=["fecha", "codigo_estacion"]).sum()), tabla)
    sin_dato = df[columna_valor].isin(CODIGOS_SIN_DATO)
    medidor.medir("Código de 'sin dato' (-999, 9999)", "Pasar la fila a cuarentena", int(sin_dato.sum()), 0, tabla)

    valor = df[columna_valor]
    motivo = pd.Series(pd.NA, index=df.index, dtype="object")
    reglas = [
        ("Fecha no interpretable", df["fecha"].isna()),
        ("Código de sin dato", sin_dato),
        ("Valor vacío", valor.isna()),
        ("Valor fuera de rango", (valor < minimo) | (valor > maximo)),
        ("Estación sin municipio", df["municipio"].isna()),
        ("Coordenadas vacías", df[["latitud", "longitud"]].isna().any(axis=1)),
        ("Número de observaciones inválido", df["n_obs"].isna() | (df["n_obs"] < 1)),
    ]
    for nombre, mascara in reglas:
        motivo = motivo.mask(mascara & motivo.isna(), nombre)
    medidor.medir("Valores vacíos o fuera de rango físico", "Pasar la fila a cuarentena",
                  int(motivo.isin(["Valor vacío", "Valor fuera de rango"]).sum()), 0, tabla)

    cuarentena = df[motivo.notna()].assign(motivo=motivo[motivo.notna()])
    limpias = df[motivo.isna()].copy()
    limpias["n_obs"] = limpias["n_obs"].astype(int)
    for col in ["latitud", "longitud", columna_valor]:
        limpias[col] = limpias[col].astype(float)
    for col in ["codigo_estacion", "estacion", "municipio"]:
        limpias[col] = limpias[col].astype(object)
    return limpias.reset_index(drop=True), cuarentena.reset_index(drop=True)


def limpiar_precipitacion(bronce, medidor):
    return limpiar_estacion(bronce, "ideam_precipitacion", "precipitacion_mm", "precipitacion_mm", 0, 500, medidor)


def limpiar_temperatura(bronce, medidor):
    return limpiar_estacion(bronce, "ideam_temperatura", "temperatura_c", "temperatura_c", -10, 45, medidor)


PROCESOS = [
    ("ideam_precipitacion_diaria", "ideam_precipitacion", limpiar_precipitacion, ESQUEMA_IDEAM_PRECIPITACION),
    ("ideam_temperatura_diaria", "ideam_temperatura", limpiar_temperatura, ESQUEMA_IDEAM_TEMPERATURA),
]


def main() -> None:
    medidor = Medidor()
    tablas, motivos_cuarentena = [], {}
    config.DIR_SILVER.mkdir(parents=True, exist_ok=True)
    for archivo, nombre, limpiar, esquema in PROCESOS:
        ruta = config.DIR_BRONZE / f"{archivo}.parquet"
        if not ruta.exists():
            raise FileNotFoundError(f"Falta {ruta}. Ejecute python -m src.pipeline para descargar las fuentes.")
        bronce = pd.read_parquet(ruta)
        log(f"{archivo}: {len(bronce):,} filas en bronce")
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
