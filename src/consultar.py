"""
Ejecuta las consultas SQL del proyecto con DuckDB.

Uso:
    python -m src.consultar              # consultas de consultas/oro/ sobre data/observatorio.duckdb
    python -m src.consultar --bronce     # consultas de consultas/ directo sobre los Parquet de bronce
"""
import os
import sys

import duckdb

from src import config
from src.utils import log


def main() -> None:
    os.chdir(config.RAIZ)
    sobre_bronce = "--bronce" in sys.argv
    carpeta = config.RAIZ / "consultas" if sobre_bronce else config.RAIZ / "consultas" / "oro"
    con = duckdb.connect() if sobre_bronce else duckdb.connect(str(config.RAIZ / "data" / "observatorio.duckdb"), read_only=True)
    for archivo in sorted(carpeta.glob("*.sql")):
        log(f"Consulta: {archivo.name}")
        print(con.sql(archivo.read_text(encoding="utf-8")).df().to_string(index=False))
        print()


if __name__ == "__main__":
    main()
