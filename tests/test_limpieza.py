"""
Pruebas automaticas de la capa plata (reglas de limpieza de EnerAndes).

Cada prueba es una funcion que empieza por test_. Prepara unos datos de
ejemplo pequenos, ejecuta una funcion del proyecto y comprueba con assert
que el resultado es el esperado. No necesitan internet ni los archivos de
data/: se ejecutan en segundos.

Uso:
    python -m pytest -v
"""
# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
import pandas as pd     # pandas: para armar una tabla de ejemplo
import pandera.errors   # los errores que lanza pandera cuando una regla falla
import pytest           # pytest: la libreria que encuentra y ejecuta las pruebas

from src.quality.esquemas import ESQUEMA_VENTAS               # el esquema de la capa plata
from src.silver.enerandes import clave_municipio, limpiar, sin_tildes   # lo que se prueba


# ---------------------------------------------------------------------------
# DATOS DE EJEMPLO
# ---------------------------------------------------------------------------
def hoja_de_ejemplo() -> pd.DataFrame:
    """Una hoja 2023 en miniatura, como queda en bronce: encabezado como fila,
    una fila repetida, una energia negativa y la fila TOTAL."""
    # Una lista de listas: cada lista de adentro es una fila de la hoja.
    # Todo va entre comillas (texto), como llega del Excel; None es una celda vacia
    filas = [
        ["Fecha", "Municipio", "Segmento", "Tipo_Compra", "Energia_kWh", "Valor_COP", "Clientes"],
        ["2023-01", "Medellín", "Residencial", "Contrato", "1000", "900000", "10"],
        ["2023-01", "Medellín", "Residencial", "Contrato", "1000", "900000", "10"],   # repetida
        ["2023-01", "ITAGUI", "RESID.", "bolsa", "500", "450000", "5"],
        ["2023-02", "Rio Negro", "IND", "CONTRATOS", "-300", "270000", "2"],         # negativa
        ["TOTAL", None, None, None, "1200", "1620000", "17"],                        # total
    ]
    # pd.DataFrame(filas, columns=...) convierte la lista en una tabla.
    # [f"col_{i}" for i in range(7)] arma los nombres col_0 ... col_6, igual que en bronce
    return pd.DataFrame(filas, columns=[f"col_{i}" for i in range(7)])


# ---------------------------------------------------------------------------
# PRUEBAS
# ---------------------------------------------------------------------------
def test_sin_tildes_quita_tildes_mayusculas_y_espacios():
    # 1. Arrange (Preparar): dos textos escritos "mal": con espacios, mayusculas y tildes
    texto1 = " ITAGÜÍ "
    texto2 = "Medellín"
    # 2. Act (Ejecutar): la funcion que se prueba, con cada texto
    resultado1 = sin_tildes(texto1)
    resultado2 = sin_tildes(texto2)
    # 3. Assert (Comprobar): assert A == B: si A es igual a B, sigue; si no, la prueba falla.
    # Los dos deben quedar sin espacios, sin tildes y en minuscula
    assert resultado1 == "itagui"
    assert resultado2 == "medellin"


def test_clave_municipio_resuelve_los_alias():
    # 1. Arrange (Preparar): dos alias de la lista ALIAS_MUNICIPIO y una celda vacia (None)
    alias1 = "Rio Negro"
    alias2 = "Medellín D.E."
    vacio = None
    # 2. Act (Ejecutar): la funcion que se prueba, con cada valor
    clave1 = clave_municipio(alias1)
    clave2 = clave_municipio(alias2)
    clave3 = clave_municipio(vacio)
    # 3. Assert (Comprobar): cada alias da su clave; la celda vacia da None.
    # "is None" pregunta si no tiene valor
    assert clave1 == "rionegro"
    assert clave2 == "medellin"
    assert clave3 is None


def test_limpiar_quita_encabezado_total_y_duplicados():
    # 1. Arrange (Preparar): la hoja 2023 en miniatura (con encabezado, TOTAL y una repetida)
    hoja = hoja_de_ejemplo()
    # 2. Act (Ejecutar): la limpieza completa. limpiar() devuelve tres cosas
    # y se reciben en tres variables
    limpias, cuarentena, metricas = limpiar(hoja)
    # 3. Assert (Comprobar): len(limpias) es el numero de filas.
    # 5 filas de datos - 1 TOTAL - 1 repetida - 1 negativa = 2 limpias
    assert len(limpias) == 2
    # .values son los valores de la columna periodo; "not in" pregunta que NO este
    assert "TOTAL" not in limpias["periodo"].values


def test_limpiar_unifica_valores_y_pone_divipola():
    # 1. Arrange (Preparar): la hoja en miniatura (trae 'ITAGUI', 'RESID.' y 'bolsa')
    hoja = hoja_de_ejemplo()
    # 2. Act (Ejecutar): la limpieza. El _ recibe lo que esta prueba no necesita
    # (cuarentena y metricas)
    limpias, _, _ = limpiar(hoja)
    # limpias["municipio"] == "Itagüí" da True en las filas de Itagui;
    # limpias[...] deja solo esas filas; .iloc[0] toma la primera (posicion 0)
    itagui = limpias[limpias["municipio"] == "Itagüí"].iloc[0]
    # 3. Assert (Comprobar): 'ITAGUI' recibio su codigo DIVIPOLA,
    # 'RESID.' quedo como 'Residencial' y 'bolsa' como 'Bolsa'
    assert itagui["divipola"] == "05360"
    assert itagui["segmento"] == "Residencial"
    assert itagui["tipo_compra"] == "Bolsa"


def test_energia_negativa_va_a_cuarentena():
    # 1. Arrange (Preparar): la hoja en miniatura (trae una energia de -300)
    hoja = hoja_de_ejemplo()
    # 2. Act (Ejecutar): la limpieza. Esta prueba solo necesita la cuarentena: lo demas va a _
    _, cuarentena, _ = limpiar(hoja)
    # 3. Assert (Comprobar): solo una fila tenia energia negativa, y es la de -300.
    # .iloc[0] es la primera fila de la cuarentena
    assert len(cuarentena) == 1
    assert cuarentena.iloc[0]["energia_kwh"] == -300


def test_pandera_rechaza_un_tipo_de_compra_invalido():
    # 1. Arrange (Preparar): una tabla limpia, y se le dana a proposito una celda.
    # .loc[0, "tipo_compra"] es la celda de la fila 0, columna tipo_compra;
    # se le pone un valor que no esta permitido
    limpias, _, _ = limpiar(hoja_de_ejemplo())
    limpias.loc[0, "tipo_compra"] = "CONTRATOS"
    # 2. Act (Ejecutar) y 3. Assert (Comprobar) van juntos en esta prueba:
    # with pytest.raises(...): la prueba ESPERA ese error dentro del bloque.
    # Si pandera lanza SchemaErrors, la prueba pasa; si no lo lanza, falla
    with pytest.raises(pandera.errors.SchemaErrors):
        # Revisa la tabla danada con las reglas de pandera
        ESQUEMA_VENTAS.validate(limpias, lazy=True)
