"""Prompts del coach, en ficheros de texto versionados.

El prompt de sistema es estable (no lleva fechas ni datos de la atleta) para que el proveedor
pueda cachearlo junto con las herramientas. Los datos variables van en el primer mensaje.
"""

from functools import cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent


@cache
def load(name: str) -> str:
    return (_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def system_prompt(*, intake: bool) -> str:
    base = load("system")
    return f"{base}\n\n{load('intake')}" if intake else base
