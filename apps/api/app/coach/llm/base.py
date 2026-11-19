"""Interfaz común de los proveedores de LLM, con llamadas a herramientas.

Los tipos son neutros: el orquestador no sabe qué proveedor hay detrás. Cada proveedor traduce
a su API y devuelve el uso de tokens tal como lo factura (entrada sin caché, escritura y
lectura de caché, salida), para calcular el coste con los precios oficiales.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolResult:
    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Un turno. `user` lleva texto y/o resultados de herramientas; `assistant`, texto y/o
    llamadas. `provider_content` es el contenido original del proveedor para reenviarlo tal
    cual dentro de la misma respuesta (p. ej. bloques de razonamiento); no se guarda."""

    role: Literal["user", "assistant"]
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()
    provider_content: Any = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def prompt_tokens(self) -> int:
        """Tokens de entrada totales (con la caché): el tamaño del prompt."""
        return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens

    def __add__(self, other: "LLMUsage") -> "LLMUsage":
        return LLMUsage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.cache_read_tokens + other.cache_read_tokens,
            self.cache_write_tokens + other.cache_write_tokens,
        )


@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str
    tool_calls: tuple[ToolCall, ...]
    usage: LLMUsage
    model: str
    stop_reason: str
    provider_content: Any = field(default=None, compare=False)

    def as_message(self) -> ChatMessage:
        return ChatMessage(
            role="assistant",
            text=self.text,
            tool_calls=self.tool_calls,
            provider_content=self.provider_content,
        )


class LLMError(Exception):
    """Fallo del proveedor (red, límite de peticiones, respuesta rechazada…).

    `usage` es lo que se haya consumido antes del fallo, para registrarlo igualmente. El
    mensaje nunca incluye el prompt ni la clave.
    """

    def __init__(self, message: str, *, usage: LLMUsage | None = None):
        super().__init__(message)
        self.usage = usage


class LLMProvider(Protocol):
    """Un proveedor de LLM. El modelo se elige en cada llamada (viene de la configuración)."""

    name: str

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
        max_tokens: int,
        effort: str | None = None,
    ) -> LLMResponse: ...
