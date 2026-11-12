"""
Capa plata: indice ONI de NOAA.

El ONI llega por trimestres moviles (DJF = diciembre, enero y febrero). Cada trimestre se asigna a su
mes central (DJF -> enero) para dejar un valor por mes, y se agrega la fase del fenomeno.

Uso:
    python -m src.silver.noaa
"""
import pandas as pd

from src import config
from src.quality import calidad
from src.quality.calidad import Medidor
from src.quality.esquemas import ESQUEMA_NOAA_ONI
from src.utils import log

LINAJE = ["_fuente", "_origen", "_extraido_en"]
FUENTE = "NOAA"
UMBRAL_ENSO = 0.5

MES_CENTRAL = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}


def fase_enso(oni: float) -> str:
    """El Niño si el ONI es >= 0,5; La Niña si es <= -0,5; Neutral en los demás casos."""
    if oni >= UMBRAL_ENSO:
        return "El Niño"
    if oni <= -UMBRAL_ENSO:
        return "La Niña"
    return "Neutral"


def limpiar(bronce: pd.DataFrame, medidor: Medidor) -> tuple[pd.DataFrame, pd.DataFrame]:
    tabla = "noaa_oni"
    datos = bronce.drop(columns=LINAJE, errors="ignore")
    texto_antes = calidad.contar_texto(datos["YR"]) + calidad.contar_texto(datos["ANOM"])
    df = pd.DataFrame({
        "trimestre_movil": datos["SEAS"].astype("string").str.strip().str.upper(),
        "anio": pd.to_numeric(datos["YR"], errors="coerce"),
        "oni": pd.to_numeric(datos["ANOM"], errors="coerce"),
    })
    medidor.medir("Año y anomalía guardados como texto", "Convertir a número", texto_antes,
                  calidad.contar_texto(df["anio"]) + calidad.contar_texto(df["oni"]), tabla)

    df["mes"] = df["trimestre_movil"].map(MES_CENTRAL)
    medidor.medir("Trimestres móviles (DJF, JFM...)", "Asignar cada trimestre a su mes central (DJF -> enero)",
                  int(df["trimestre_movil"].nunique()), int(df["mes"].nunique()), tabla)

    antes = int(df.duplicated(subset=["anio", "mes"]).sum())
    df = df.drop_duplicates(subset=["anio", "mes"])
    medidor.medir("Meses repetidos", "Dejar un valor por mes", antes, int(df.duplicated(subset=["anio", "mes"]).sum()), tabla)

    invalidas = df["anio"].isna() | df["mes"].isna() | df["oni"].isna()
    medidor.medir("Trimestres sin año, mes o ONI válido", "Pasar la fila a cuarentena", int(invalidas.sum()), 0, tabla)
    cuarentena = df[invalidas].assign(motivo="Trimestre, año u ONI no válido")
    df = df[~invalidas].copy()

    df["anio"] = df["anio"].astype(int)
    df["mes"] = df["mes"].astype(int)
    df["oni"] = df["oni"].astype(float)
    df["fecha"] = pd.to_datetime(dict(year=df["anio"], month=df["mes"], day=1))
    df["trimestre_movil"] = df["trimestre_movil"].astype(object)
    df["fase_enso"] = df["oni"].map(fase_enso)
    medidor.medir("Meses sin fase del fenómeno", "Calcular la fase con los umbrales +0,5 y -0,5", len(df),
                  int(df["fase_enso"].isna().sum()), tabla)
    orden = ["fecha", "anio", "mes", "trimestre_movil", "oni", "fase_enso"]
    return df.sort_values("fecha")[orden].reset_index(drop=True), cuarentena.reset_index(drop=True)


def main() -> None:
    medidor = Medidor()
    bronce = pd.read_parquet(config.DIR_BRONZE / "noaa_oni.parquet")
    log(f"noaa_oni: {len(bronce):,} filas en bronce")
    limpias, cuarentena = limpiar(bronce, medidor)
    ESQUEMA_NOAA_ONI.validate(limpias, lazy=True)
    log("Validación con pandera: OK")
    config.DIR_SILVER.mkdir(parents=True, exist_ok=True)
    limpias.to_parquet(config.DIR_SILVER / "noaa_oni.parquet", index=False)
    cuarentena.to_parquet(config.DIR_SILVER / "noaa_oni_cuarentena.parquet", index=False)
    calidad.guardar(
        FUENTE,
        [{"tabla": "noaa_oni", "bronce": len(bronce), "plata": len(limpias), "cuarentena": len(cuarentena)}],
        medidor.filas,
        {"noaa_oni": cuarentena["motivo"].value_counts().to_dict() if len(cuarentena) else {}},
    )
    log(f"Plata: {len(limpias):,} meses, cuarentena: {len(cuarentena)}")


if __name__ == "__main__":
    main()
