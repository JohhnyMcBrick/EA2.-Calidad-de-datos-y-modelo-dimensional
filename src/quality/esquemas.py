"""Esquemas de pandera de la capa plata: las condiciones que cada tabla limpia debe cumplir."""
import pandera.pandas as pa
from pandera.pandas import Check, Column

SEGMENTOS = ["Residencial", "Comercial", "Industrial", "No informado"]
TIPOS_COMPRA = ["Bolsa", "Contrato"]
FASES_ENSO = ["El Niño", "La Niña", "Neutral"]
TRIMESTRES_MOVILES = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]

PERIODO = r"^(2023|2024|2025|2026)-(0[1-9]|1[0-2])$"
HORAS = Check.in_range(0, 23)


def _no_vacio(s):
    return s.str.strip().str.len() > 0


ESQUEMA_VENTAS = pa.DataFrameSchema(
    {
        "periodo": Column(str, Check.str_matches(PERIODO)),
        "divipola": Column(str, Check.str_matches(r"^\d{5}$")),
        "municipio": Column(str, Check(_no_vacio)),
        "segmento": Column(str, Check.isin(SEGMENTOS)),
        "tipo_compra": Column(str, Check.isin(TIPOS_COMPRA)),
        "energia_kwh": Column(float, Check.ge(0)),
        "valor_cop": Column(float, Check.ge(0), nullable=True),
        "clientes": Column(int, Check.ge(0)),
    },
    checks=Check(
        lambda df: (df["valor_cop"] / df["energia_kwh"]).dropna().between(500, 2000),
        error="tarifa implicita (valor_cop / energia_kwh) fuera de 500 a 2000 COP por kWh",
    ),
    unique=["periodo", "divipola", "segmento", "tipo_compra"],
    strict=True,
)

ESQUEMA_XM_PRECIO = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "hora": Column(int, HORAS),
        "precio_cop_kwh": Column(float, Check.in_range(0, 10000)),
    },
    unique=["fecha", "hora"],
    strict=True,
)

ESQUEMA_XM_DEMANDA = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "hora": Column(int, HORAS),
        "demanda_kwh": Column(float, Check.in_range(0, 30_000_000)),
    },
    unique=["fecha", "hora"],
    strict=True,
)

ESQUEMA_XM_GENERACION = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "hora": Column(int, HORAS),
        "codigo_recurso": Column(str, Check(_no_vacio)),
        "generacion_kwh": Column(float, Check.in_range(0, 5_000_000)),
    },
    unique=["fecha", "hora", "codigo_recurso"],
    strict=True,
)

ESQUEMA_XM_EMBALSES = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "embalses_pct": Column(float, Check.in_range(0, 100)),
    },
    unique=["fecha"],
    strict=True,
)

ESQUEMA_XM_APORTES = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "aportes_kwh": Column(float, Check.ge(0)),
    },
    unique=["fecha"],
    strict=True,
)

ESQUEMA_XM_RECURSOS = pa.DataFrameSchema(
    {
        "codigo_recurso": Column(str, Check(_no_vacio)),
        "nombre_recurso": Column(str, Check(_no_vacio)),
        "tipo_recurso": Column(str, Check(_no_vacio)),
        "estado": Column(str, nullable=True, required=False),
        "fecha_operacion": Column("datetime64[ns]", nullable=True, required=False),
    },
    unique=["codigo_recurso"],
    strict=False,
)

_ESTACION = {
    "fecha": Column("datetime64[ns]"),
    "codigo_estacion": Column(str, Check.str_matches(r"^\d+$")),
    "estacion": Column(str, Check(_no_vacio)),
    "municipio": Column(str, Check(_no_vacio)),
    "latitud": Column(float, Check.in_range(-5, 14)),
    "longitud": Column(float, Check.in_range(-82, -66)),
}

ESQUEMA_IDEAM_PRECIPITACION = pa.DataFrameSchema(
    {
        **_ESTACION,
        "precipitacion_mm": Column(float, Check.in_range(0, 500)),
        "n_obs": Column(int, Check.ge(1)),
    },
    unique=["fecha", "codigo_estacion"],
    strict=True,
)

ESQUEMA_IDEAM_TEMPERATURA = pa.DataFrameSchema(
    {
        **_ESTACION,
        "temperatura_c": Column(float, Check.in_range(-10, 45)),
        "n_obs": Column(int, Check.ge(1)),
    },
    unique=["fecha", "codigo_estacion"],
    strict=True,
)

ESQUEMA_NOAA_ONI = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "anio": Column(int, Check.in_range(1950, 2100)),
        "mes": Column(int, Check.in_range(1, 12)),
        "trimestre_movil": Column(str, Check.isin(TRIMESTRES_MOVILES)),
        "oni": Column(float, Check.in_range(-3.5, 4.5)),
        "fase_enso": Column(str, Check.isin(FASES_ENSO)),
    },
    checks=[
        Check(
            lambda df: ((df["oni"] >= 0.5) == (df["fase_enso"] == "El Niño")).all(),
            error="fase El Niño inconsistente con el umbral ONI >= 0.5",
        ),
        Check(
            lambda df: ((df["oni"] <= -0.5) == (df["fase_enso"] == "La Niña")).all(),
            error="fase La Niña inconsistente con el umbral ONI <= -0.5",
        ),
    ],
    unique=["anio", "mes"],
    strict=True,
)
