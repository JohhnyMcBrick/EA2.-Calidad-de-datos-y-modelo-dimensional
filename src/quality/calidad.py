"""Registro de metricas de calidad: cada limpieza las guarda y el reporte las lee."""
import json
from dataclasses import dataclass, field

from src import config

DIR_CALIDAD = config.DIR_SILVER / "_calidad"


@dataclass
class Medidor:
    """Acumula las metricas antes y despues de cada regla de limpieza."""

    filas: list[dict] = field(default_factory=list)

    def medir(self, problema: str, regla: str, antes: int, despues: int, tabla: str | None = None) -> None:
        fila = {"problema": problema, "regla aplicada": regla, "antes": int(antes), "despues": int(despues)}
        if tabla:
            fila["tabla"] = tabla
        self.filas.append(fila)


def contar_texto(serie) -> int:
    """Cuantas celdas de la serie son texto (str) y no numero o fecha."""
    return int(serie.map(lambda v: isinstance(v, str)).sum())


def combinar(metricas: list[dict]) -> list[dict]:
    """Suma las metricas con el mismo problema y la misma regla, conservando el orden."""
    acumulado: dict[tuple, dict] = {}
    for m in metricas:
        clave = (m.get("tabla"), m["problema"], m["regla aplicada"])
        if clave in acumulado:
            acumulado[clave]["antes"] += m["antes"]
            acumulado[clave]["despues"] += m["despues"]
        else:
            acumulado[clave] = dict(m)
    return list(acumulado.values())


def guardar(fuente: str, tablas: list[dict], metricas: list[dict], cuarentena: dict[str, dict[str, int]]) -> None:
    """Escribe data/silver/_calidad/<fuente>.json con lo que necesita el reporte."""
    DIR_CALIDAD.mkdir(parents=True, exist_ok=True)
    contenido = {"fuente": fuente, "tablas": tablas, "metricas": metricas, "cuarentena": cuarentena}
    (DIR_CALIDAD / f"{fuente}.json").write_text(
        json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def leer(fuente: str) -> dict | None:
    ruta = DIR_CALIDAD / f"{fuente}.json"
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))
