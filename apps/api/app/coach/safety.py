"""Filtro de seguridad determinista, antes del LLM.

Si el mensaje habla de dolor torácico, mareo, desmayo o una lesión aguda, el coach no llama al
LLM: da una respuesta fija que recomienda una valoración médica y no toca el plan. Es
deliberadamente conservador: una negación («no me duele el pecho») también salta. Mejor un
aviso de más que uno de menos.

Las expresiones se buscan sobre el texto normalizado (`search_key`: minúsculas, sin acentos ni
signos), con límites de palabra.
"""

import enum
import re
from dataclasses import dataclass

from app.core.text import search_key


class RedFlag(enum.StrEnum):
    CHEST_PAIN = "chest_pain"
    DIZZINESS = "dizziness"
    FAINTING = "fainting"
    ACUTE_INJURY = "acute_injury"


_PATTERNS: dict[RedFlag, tuple[str, ...]] = {
    RedFlag.CHEST_PAIN: (
        r"dolor (?:\w+ )?(?:en el|del) pecho",
        r"me duele (?:\w+ )?el pecho",
        r"dolor (?:\w+ )?toracico",
        r"(?:opresion|presion|pinchazo|pinchazos) en el pecho",
        r"angina",
        r"palpitaciones",
        r"chest pain",
    ),
    RedFlag.DIZZINESS: (
        r"mare(?:o|os|e|ado|ada|ados|adas|aba|arme|andome)",
        r"vertigos?",
        r"(?:se me|me) (?:va|iba|fue) la cabeza",
        r"dizz(?:y|iness)",
    ),
    RedFlag.FAINTING: (
        r"desmay(?:o|os|e|ado|ada|arme|ando)",
        r"me (?:he )?desmay\w*",
        r"perd(?:i|ido) (?:el )?(?:conocimiento|sentido)",
        r"sincope",
        r"lipotimia",
        r"faint(?:ed|ing)?",
    ),
    RedFlag.ACUTE_INJURY: (
        r"lesion aguda",
        r"rotura",
        r"me he roto",
        r"me rompi",
        r"fractura\w*",
        r"esguince",
        r"(?:he oido|note|senti) un (?:chasquido|crujido)",
        r"no puedo apoyar",
        r"no puedo (?:andar|caminar)",
        r"(?:muy|mucho) hinchad[oa]",
        r"me (?:he )?(?:torcido|dislocado)",
        r"(?:luxacion|dislocacion)",
        r"\bcaida\b.*\b(?:golpe|herida|sangr\w*)",
    ),
}

_COMPILED = {
    flag: tuple(re.compile(rf"\b(?:{pattern})\b") for pattern in patterns)
    for flag, patterns in _PATTERNS.items()
}

SAFETY_REPLY = (
    "Lo que cuentas puede necesitar una valoración médica, así que no voy a darte "
    "recomendaciones de entrenamiento sobre esto. Para el entrenamiento por ahora y consulta a "
    "un profesional sanitario. Si tienes dolor en el pecho, te desmayas, te mareas de forma "
    "intensa o te falta el aire, llama al 112 o acude a urgencias. Cuando te hayan valorado, "
    "cuéntame qué te han dicho y lo tenemos en cuenta para el plan."
)


@dataclass(frozen=True, slots=True)
class SafetyResult:
    flags: tuple[RedFlag, ...]

    @property
    def triggered(self) -> bool:
        return bool(self.flags)


def check_message(text: str) -> SafetyResult:
    key = search_key(text)
    flags = tuple(
        flag for flag, patterns in _COMPILED.items() if any(p.search(key) for p in patterns)
    )
    return SafetyResult(flags)
