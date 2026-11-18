"""Utilidades de texto puras (sin BD)."""

import re
import unicodedata

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def search_key(text: str) -> str:
    """Forma normalizada para buscar sin distinguir mayúsculas, acentos ni signos.

    «Peso muerto rumano», «PESO-MUERTO rumáno» y « peso   muerto  rumano » dan lo mismo:
    `peso muerto rumano`. La ñ pasa a n. Todo lo que no es letra o número es un espacio.
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _NON_ALNUM.sub(" ", stripped).strip()


def search_text(name: str, aliases: list[str]) -> str:
    """Texto de búsqueda de un ejercicio: el nombre y los alias normalizados, separados por `|`.

    El separador no puede aparecer en una clave normalizada, así que una búsqueda nunca casa
    a caballo entre dos alias.
    """
    keys = [search_key(name), *(search_key(alias) for alias in aliases)]
    return "|".join(key for key in keys if key)
