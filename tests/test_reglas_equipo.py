"""Pruebas de las reglas de limpieza agregadas por el equipo (4 hojas de EnerAndes, XM, IDEAM y NOAA)."""
import pandas as pd
import pandera.errors
import pytest

from src.quality.calidad import Medidor, combinar
from src.quality.esquemas import ESQUEMA_NOAA_ONI, ESQUEMA_VENTAS, ESQUEMA_XM_PRECIO
from src.silver import enerandes, ideam, noaa, xm


def hoja_2024() -> pd.DataFrame:
    filas = [
        ["PERIODO", "MUNICIPIO", "SEGMENTO CLIENTE", "MODALIDAD", "ENERGIA", "UNIDAD", "VALOR ($)", "NUM CLIENTES"],
        ["mar-24", "Bello", "Residencial", "Contrato", "1.5", "MWh", "1500000", "10"],
        ["03/2024", "Caldas", "Comercial", "Bolsa", "2000", "kWh", "2000000", "4"],
        ["TOTAL", None, None, None, None, None, None, None],
    ]
    return pd.DataFrame(filas, columns=[f"col_{i}" for i in range(8)])


def hoja_2025_con_titulos() -> pd.DataFrame:
    filas = [
        ["EnerAndes S.A.S. E.S.P. - Reporte de ventas 2025", None, None, None, None, None, None],
        ["Fuente: sistema comercial. Uso interno.", None, None, None, None, None, None],
        [None, None, None, None, None, None, None],
        ["mes", "municipio", "segmento", "tipo compra", "consumo (kWh)", "facturado", "usuarios"],
        ["06/2025", "Apartadó", "Comercial", "Bolsa", "121318", "143967156", "87"],
    ]
    return pd.DataFrame(filas, columns=[f"col_{i}" for i in range(7)])


def hoja_2026() -> pd.DataFrame:
    filas = [
        ["Fecha corte", "Ciudad", "Tipo cliente", "Compra", "kWh", "Total facturado COP", "Clientes activos"],
        ["01/03/2026", "Turbo", "Industrial", "Bolsa", "129004", "138379114", "3"],
    ]
    return pd.DataFrame(filas, columns=[f"col_{i}" for i in range(7)])


def test_energia_en_mwh_se_convierte_a_kwh():
    limpias, _, _ = enerandes.limpiar(hoja_2024(), hoja="2024")
    bello = limpias[limpias["municipio"] == "Bello"].iloc[0]
    assert bello["energia_kwh"] == 1500.0


@pytest.mark.parametrize("texto, esperado", [
    ("mar-24", "2024-03"),
    ("jan-24", "2024-01"),
    ("dic-24", "2024-12"),
    ("03/2024", "2024-03"),
    ("2024-03", "2024-03"),
])
def test_los_formatos_de_fecha_dan_el_mismo_periodo(texto, esperado):
    assert enerandes.parsear_periodo(texto) == esperado


def test_fecha_de_corte_dia_mes_anio_se_lee_como_marzo():
    assert enerandes.parsear_periodo("01/03/2026") == "2026-03"
    assert enerandes.parsear_periodo("01/12/2026") == "2026-12"


def test_fecha_invalida_no_se_interpreta():
    assert enerandes.parsear_periodo("xyz-24") is None
    assert enerandes.parsear_periodo("13/2024") is None
    assert enerandes.parsear_periodo(None) is None


def test_encabezado_se_ubica_debajo_de_los_titulos():
    hoja = hoja_2025_con_titulos()
    assert enerandes.ubicar_encabezado(hoja) == 3
    limpias, _, metricas = enerandes.limpiar(hoja, hoja="2025")
    assert list(limpias.columns) == enerandes.ORDEN
    titulos = next(m for m in metricas if m["problema"].startswith("Filas de título"))
    assert titulos["antes"] == 3


def test_las_hojas_con_encabezados_distintos_quedan_en_una_sola_tabla():
    hojas = {"2024": hoja_2024(), "2025": hoja_2025_con_titulos(), "2026": hoja_2026()}
    limpias, cuarentena, _ = enerandes.limpiar_todas(hojas)
    assert len(limpias) == 4
    assert len(cuarentena) == 0
    assert sorted(limpias["periodo"]) == ["2024-03", "2024-03", "2025-06", "2026-03"]


def test_una_venta_repetida_en_dos_formatos_de_fecha_queda_una_vez():
    filas = [
        ["PERIODO", "MUNICIPIO", "SEGMENTO CLIENTE", "MODALIDAD", "ENERGIA", "UNIDAD", "VALOR ($)", "NUM CLIENTES"],
        ["mar-24", "Bello", "Comercial", "Bolsa", "1000", "kWh", "900000", "5"],
        ["03/2024", "Bello ", "COMERCIAL", "bolsa", "1", "MWh", "900000", "5"],
    ]
    hoja = pd.DataFrame(filas, columns=[f"col_{i}" for i in range(8)])
    limpias, _, metricas = enerandes.limpiar(hoja, hoja="2024")
    assert len(limpias) == 1
    assert next(m for m in metricas if m["problema"] == "Filas duplicadas")["antes"] == 1


def test_municipio_desconocido_va_a_cuarentena_sin_detener_la_limpieza():
    hoja = hoja_2026()
    hoja.loc[1, "col_1"] = "Ciudad Inventada"
    limpias, cuarentena, _ = enerandes.limpiar(hoja, hoja="2026")
    assert len(limpias) == 0
    assert cuarentena.iloc[0]["motivo"] == "Municipio no reconocido"


def test_energia_vacia_va_a_cuarentena_con_su_motivo():
    hoja = hoja_2026()
    hoja.loc[1, "col_4"] = None
    _, cuarentena, _ = enerandes.limpiar(hoja, hoja="2026")
    assert cuarentena.iloc[0]["motivo"] == "Energía vacía"
    assert cuarentena.iloc[0]["hoja"] == "2026"


def test_pandera_rechaza_una_tarifa_imposible():
    limpias, _, _ = enerandes.limpiar(hoja_2026(), hoja="2026")
    limpias.loc[0, "valor_cop"] = 5.0
    with pytest.raises(pandera.errors.SchemaErrors):
        ESQUEMA_VENTAS.validate(limpias, lazy=True)


@pytest.mark.parametrize("oni, fase", [
    (1.2, "El Niño"), (0.5, "El Niño"), (0.49, "Neutral"), (0.0, "Neutral"),
    (-0.49, "Neutral"), (-0.5, "La Niña"), (-1.8, "La Niña"),
])
def test_fase_enso_segun_el_umbral_del_oni(oni, fase):
    assert noaa.fase_enso(oni) == fase


def test_trimestre_movil_se_asigna_a_su_mes_central():
    bronce = pd.DataFrame({
        "SEAS": ["DJF", "JFM", "NDJ"], "YR": ["2024", "2024", "2024"],
        "TOTAL": ["27.1", "27.0", "26.0"], "ANOM": ["1.8", "0.2", "-0.6"],
    })
    limpias, _ = noaa.limpiar(bronce, Medidor())
    assert list(limpias["mes"]) == [1, 2, 12]
    assert list(limpias["fecha"]) == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01"), pd.Timestamp("2024-12-01")]
    assert list(limpias["fase_enso"]) == ["El Niño", "Neutral", "La Niña"]
    ESQUEMA_NOAA_ONI.validate(limpias, lazy=True)


def test_pandera_rechaza_una_fase_enso_inconsistente_con_el_oni():
    bronce = pd.DataFrame({"SEAS": ["DJF"], "YR": ["2024"], "TOTAL": ["27"], "ANOM": ["1.8"]})
    limpias, _ = noaa.limpiar(bronce, Medidor())
    limpias.loc[0, "fase_enso"] = "Neutral"
    with pytest.raises(pandera.errors.SchemaErrors):
        ESQUEMA_NOAA_ONI.validate(limpias, lazy=True)


def bronce_xm() -> pd.DataFrame:
    horas = {f"Hour{h:02d}": str(h * 10.0) for h in range(1, 25)}
    return pd.DataFrame([
        {"Date": "2026-01-01", "Id": "Sistema", **horas},
        {"Date": "2026-01-02", "Id": "Sistema", **horas},
    ])


def test_xm_pasa_de_24_columnas_a_una_fila_por_hora():
    largo = xm.pasar_a_filas_por_hora(bronce_xm(), "precio_cop_kwh", None)
    assert len(largo) == 48
    primera = largo[(largo["fecha"] == "2026-01-01") & (largo["hora"] == 0)].iloc[0]
    ultima = largo[(largo["fecha"] == "2026-01-01") & (largo["hora"] == 23)].iloc[0]
    assert primera["precio_cop_kwh"] == "10.0"
    assert ultima["precio_cop_kwh"] == "240.0"


def test_xm_precio_separa_vacios_negativos_y_valores_fuera_de_rango():
    bronce = bronce_xm()
    bronce.loc[0, "Hour01"] = None
    bronce.loc[0, "Hour02"] = "-3"
    bronce.loc[0, "Hour03"] = "99999"
    limpias, cuarentena = xm.limpiar_precio(bronce, Medidor())
    assert len(limpias) == 45
    assert sorted(cuarentena["motivo"]) == ["Valor fuera de rango", "Valor negativo", "Valor vacío"]
    assert limpias["precio_cop_kwh"].dtype == float
    ESQUEMA_XM_PRECIO.validate(limpias, lazy=True)


def test_xm_quita_la_hora_repetida():
    bronce = pd.concat([bronce_xm(), bronce_xm().iloc[[0]]], ignore_index=True)
    limpias, _ = xm.limpiar_precio(bronce, Medidor())
    assert len(limpias) == 48


def test_pandera_rechaza_una_hora_fuera_de_0_a_23():
    limpias, _ = xm.limpiar_precio(bronce_xm(), Medidor())
    limpias.loc[0, "hora"] = 24
    with pytest.raises(pandera.errors.SchemaErrors):
        ESQUEMA_XM_PRECIO.validate(limpias, lazy=True)


def test_xm_embalses_pasa_de_fraccion_a_porcentaje():
    bronce = pd.DataFrame({"Date": ["2026-01-01"], "Id": ["Sistema"], "Value": ["0.6523"]})
    limpias, _ = xm.limpiar_embalses(bronce, Medidor())
    assert limpias.iloc[0]["embalses_pct"] == pytest.approx(65.23)


def test_catalogo_de_recursos_renombra_columnas_y_une_codigos_repetidos():
    bronce = pd.DataFrame({
        "Date": ["2026-03-31"] * 3,
        "Values_Code": ["gvio ", "GVIO", "TBST"],
        "Values_Name": ["GUAVIO", "GUAVIO", "TEBSA"],
        "Values_Type": ["hidraulica", "HIDRAULICA", "TERMICA"],
    })
    limpias, _ = xm.limpiar_recursos(bronce, Medidor())
    assert list(limpias["codigo_recurso"]) == ["GVIO", "TBST"]
    assert limpias.iloc[0]["tipo_recurso"] == "HIDRAULICA"


def bronce_ideam() -> pd.DataFrame:
    return pd.DataFrame({
        "codigoestacion": ["0027015030", "0027015030", "0027015030"],
        "nombreestacion": ["Aeropuerto Olaya Herrera"] * 3,
        "municipio": ["Medellín", None, "MEDELLIN"],
        "latitud": ["6.22"] * 3,
        "longitud": ["-75.59"] * 3,
        "fecha": ["2026-06-01T00:00:00.000", "2026-06-02T00:00:00.000", "2026-06-03T00:00:00.000"],
        "precipitacion_mm": ["3.5", "-999", "0.0"],
        "n_obs": ["144", "144", "144"],
    })


def test_ideam_convierte_fechas_y_completa_el_municipio_de_la_estacion():
    limpias, _ = ideam.limpiar_precipitacion(bronce_ideam(), Medidor())
    assert str(limpias["fecha"].dtype).startswith("datetime64")
    assert set(limpias["municipio"]) == {"MEDELLIN"}
    assert limpias["precipitacion_mm"].dtype == float


def test_ideam_el_codigo_sin_dato_va_a_cuarentena():
    limpias, cuarentena = ideam.limpiar_precipitacion(bronce_ideam(), Medidor())
    assert len(limpias) == 2
    assert list(cuarentena["motivo"]) == ["Código de sin dato"]


def test_combinar_suma_las_metricas_de_la_misma_regla():
    metricas = [
        {"problema": "Filas de totales", "regla aplicada": "Eliminarlas", "antes": 1, "despues": 0},
        {"problema": "Filas de totales", "regla aplicada": "Eliminarlas", "antes": 1, "despues": 0},
        {"problema": "Filas duplicadas", "regla aplicada": "Dejar una sola copia", "antes": 5, "despues": 0},
    ]
    resultado = combinar(metricas)
    assert len(resultado) == 2
    assert resultado[0]["antes"] == 2


def test_generacion_usa_el_codigo_de_planta_cuando_existe_la_columna_code():
    from src.quality.calidad import Medidor
    horas = {f"Hour{h:02d}": ["10"] * 2 for h in range(1, 25)}
    bronce = pd.DataFrame({"Date": ["2026-01-01"] * 2, "Id": ["Recurso"] * 2,
                           "code": ["ALBAN", "GUAVIO"], **horas})
    limpias, _ = xm.limpiar_generacion(bronce, Medidor())
    assert sorted(limpias["codigo_recurso"].unique()) == ["ALBAN", "GUAVIO"]
    assert len(limpias) == 48