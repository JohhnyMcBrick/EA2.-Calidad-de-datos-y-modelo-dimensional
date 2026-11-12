"""
Perfilamiento de la capa bronce: un diagnostico de cada archivo ANTES de limpiarlo.

Para cada archivo .parquet de data/bronze/ calcula:
  - filas y columnas
  - filas duplicadas (sin contar las columnas de linaje)
  - rango de fechas, si el archivo tiene una columna de fecha
  - por columna: porcentaje de nulos (vacios), valores distintos y un ejemplo

Muestra un resumen en pantalla y escribe las tablas completas en
docs/perfilamiento_tablas.md, listas para copiar en docs/perfilamiento.md.

Uso:
    python -m src.perfilar
"""
# ---------------------------------------------------------------------------
# IMPORTS (traer codigo que ya existe)
# ---------------------------------------------------------------------------
# pandas: la libreria de tablas; aqui lee cada archivo Parquet
import pandas as pd

# config: el archivo src/config.py; de ahi salen la carpeta de bronce y la raiz
from src import config
# log: escribe un mensaje en pantalla con la hora
from src.utils import log

# Las 3 columnas de linaje que agrega guardar_bronce(). Se quitan antes de buscar
# duplicados: _extraido_en puede ser distinta en dos filas iguales (si se
# descargaron en momentos distintos) y ocultaria que son la misma venta
LINAJE = ["_fuente", "_origen", "_extraido_en"]

# Como se llama la columna de fecha en cada fuente: Date (XM), fecha (IDEAM), YR (NOAA)
COLUMNAS_FECHA = ["Date", "fecha", "YR"]


def es_nulo(serie: pd.Series) -> pd.Series:
    """True donde la celda esta vacia: NaN (sin valor) o texto vacio ''."""
    # serie.isna() -> True si la celda no tiene valor (NaN)
    # serie.astype(str).str.strip() == "" -> la pasa a texto, le quita espacios y
    #                                        pregunta si quedo vacia: True si era '' o '   '
    # | significa "o": True si pasa cualquiera de las dos
    return serie.isna() | (serie.astype(str).str.strip() == "")


def perfil_archivo(df: pd.DataFrame) -> dict:
    """Calcula el resumen de UNA tabla: filas, columnas, duplicados y rango de fechas."""
    # Copia de la tabla sin las columnas de linaje; si alguna no existe, la ignora
    datos = df.drop(columns=LINAJE, errors="ignore")
    # Busca cual de las columnas de fecha tiene esta tabla:
    # (c for c in COLUMNAS_FECHA if c in df.columns) recorre "Date", "fecha", "YR"
    # y deja solo las que existen en la tabla; next(..., None) toma la primera,
    # o None si la tabla no tiene ninguna
    fecha = next((c for c in COLUMNAS_FECHA if c in df.columns), None)
    # Si se encontro una columna de fecha...
    if fecha:
        # Toma esa columna, quita los vacios (.dropna()) y la pasa a texto
        valores = df[fecha].dropna().astype(str)
        # El rango va de la fecha menor (.min()) a la mayor (.max()): "2026-01-01 a 2026-09-30"
        rango = f"{valores.min()} a {valores.max()}"
    # Si no tiene columna de fecha (el Excel de EnerAndes)...
    else:
        # ...lo dice asi
        rango = "sin columna de fecha"
    # Devuelve un diccionario con los 4 datos del resumen
    return {
        # len(df) = numero de filas
        "filas": len(df),
        # df.shape[1] = numero de columnas
        "columnas": df.shape[1],
        # .duplicated() da True en cada fila igual a otra anterior; .sum() las cuenta
        "duplicadas": int(datos.duplicated().sum()),
        # El rango de fechas calculado arriba
        "rango": rango,
    }


def perfil_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por columna: tipo, % de nulos, valores distintos y un ejemplo."""
    # filas: lista vacia; se le agrega una fila por cada columna de la tabla
    filas = []
    # col toma el nombre de cada columna de la tabla
    for col in df.columns:
        # Las columnas de linaje no se perfilan...
        if col in LINAJE:
            # ...continue salta a la siguiente columna
            continue
        # serie es la columna completa
        serie = df[col]
        # nulos: una columna de True/False, True en cada celda vacia
        nulos = es_nulo(serie)
        # ~ invierte los True/False: ~nulos es True en las celdas con valor;
        # serie[~nulos] deja solo esas celdas
        no_nulos = serie[~nulos]
        # Agrega un diccionario con los datos de esta columna
        filas.append({
            # El nombre de la columna
            "columna": col,
            # El tipo de dato: "texto" si pandas la guarda como texto (object o str);
            # si no, el nombre del tipo (int64, float64...)
            "tipo": "texto" if (serie.dtype == object or str(serie.dtype) in ("str", "string")) else str(serie.dtype),
            # .mean() de una columna de True/False es la proporcion de True (0.25 = 25 %);
            # * 100 lo vuelve porcentaje y round(..., 1) lo deja con 1 decimal
            "% nulos": round(100 * nulos.mean(), 1),
            # .nunique() cuenta los valores distintos
            "distintos": no_nulos.nunique(),
            # Un ejemplo: el primer valor no vacio (.iloc[0]), cortado a 30 letras ([:30]);
            # si la columna esta toda vacia, deja ""
            "ejemplo": str(no_nulos.iloc[0])[:30] if len(no_nulos) else "",
        })
    # Convierte la lista de diccionarios en una tabla de pandas
    return pd.DataFrame(filas)


def tabla_markdown(df: pd.DataFrame) -> str:
    """Convierte una tabla de pandas en una tabla Markdown (| col | col |)."""
    # Las 2 primeras lineas de la tabla Markdown:
    #   el encabezado: " | ".join(df.columns) une los nombres con " | " -> | columna | tipo | ... |
    #   el separador:  "---|" repetido una vez por columna             -> |---|---|...
    lineas = ["| " + " | ".join(df.columns) + " |",
              "|" + "---|" * len(df.columns)]
    # .iterrows() recorre la tabla fila por fila; _ es el numero de fila (no se usa)
    # y fila son los valores de esa fila
    for _, fila in df.iterrows():
        # Une los valores de la fila con " | ". .replace("|", "/") cambia cualquier |
        # que venga dentro de un valor, para que no rompa la tabla
        lineas.append("| " + " | ".join(str(v).replace("|", "/") for v in fila) + " |")
    # Une todas las lineas con saltos de linea y devuelve el texto
    return "\n".join(lineas)


def main() -> None:
    # Busca todos los .parquet de data/bronze y los ordena por nombre
    archivos = sorted(config.DIR_BRONZE.glob("*.parquet"))
    # Si la lista esta vacia (no hay archivos en bronce)...
    if not archivos:
        # ...avisa que primero hay que extraer los datos
        log("No hay archivos en data/bronze/. Primero ejecute: python -m src.pipeline")
        # ...y termina
        return

    # Avisa que empieza el perfilamiento
    log("Perfilamiento de la capa bronce")
    # El encabezado de la tabla de la pantalla, alineado en columnas
    print(f"   {'archivo':<36}{'filas':>8}{'cols':>6}{'duplic.':>9}   rango de fechas")
    # texto: lista con las lineas del archivo Markdown; empieza con el titulo
    texto = ["# Perfilamiento de la capa bronce (tablas generadas con src/perfilar.py)\n"]

    # archivo toma cada .parquet de bronce
    for archivo in archivos:
        # Lo abre como tabla
        df = pd.read_parquet(archivo)
        # Calcula su resumen: filas, columnas, duplicadas, rango
        p = perfil_archivo(df)
        # Escribe una linea del resumen en pantalla
        print(f"   {archivo.name:<36}{p['filas']:>8,}{p['columnas']:>6}{p['duplicadas']:>9}   {p['rango']}")

        # En el Markdown: un subtitulo con el nombre del archivo
        texto.append(f"\n## {archivo.name}\n")
        # En el Markdown: una linea con el resumen del archivo
        texto.append(f"- Filas: {p['filas']:,} · Columnas: {p['columnas']} · "
                     f"Filas duplicadas: {p['duplicadas']} · Rango de fechas: {p['rango']}\n")
        # En el Markdown: la tabla con el perfil de cada columna
        texto.append(tabla_markdown(perfil_columnas(df)))
        # Una linea en blanco
        texto.append("\n")

    # La ruta del archivo de salida: ...\docs\perfilamiento_tablas.md
    destino = config.RAIZ / "docs" / "perfilamiento_tablas.md"
    # .parent es la carpeta docs/; .mkdir la crea si no existe
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Une las lineas con saltos de linea y las escribe en el archivo
    destino.write_text("\n".join(texto), encoding="utf-8")
    # Avisa donde quedo; .relative_to(RAIZ) muestra la ruta desde la raiz: docs\perfilamiento_tablas.md
    log(f"Tablas completas por columna en {destino.relative_to(config.RAIZ)}")


# Solo se ejecuta main() cuando se corre este archivo (python -m src.perfilar)
if __name__ == "__main__":
    main()
