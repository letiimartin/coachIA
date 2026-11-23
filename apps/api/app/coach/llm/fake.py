"""Proveedor simulado para tests y para el CI: nunca llama a un LLM real.

Devuelve respuestas guionizadas en orden y guarda cada petición para inspeccionarla.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from app.coach.llm.base import ChatMessage, LLMError, LLMResponse, LLMUsage, ToolCall, ToolSpec


@dataclass(frozen=True, slots=True)
class FakeRequest:
    model: str
    system: str
    messages: tuple[ChatMessage, ...]
    tools: tuple[ToolSpec, ...]
    max_tokens: int
    effort: str | None


Script = LLMResponse | LLMError | Callable[[FakeRequest], LLMResponse]


def reply(
    text: str = "",
    *,
    tool_calls: Sequence[ToolCall] = (),
    usage: LLMUsage | None = None,
    model: str = "fake-model",
) -> LLMResponse:
    return LLMResponse(
        text=text,
        tool_calls=tuple(tool_calls),
        usage=usage or LLMUsage(input_tokens=1000, output_tokens=100),
        model=model,
        stop_reason="tool_use" if tool_calls else "end_turn",
    )


@dataclass
class FakeProvider:
    script: list[Script] = field(default_factory=list)
    requests: list[FakeRequest] = field(default_factory=list)
    name: str = "fake"

    def queue(self, *items: Script) -> None:
        self.script.extend(items)

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
        max_tokens: int,
        effort: str | None = None,
    ) -> LLMResponse:
        request = FakeRequest(model, system, tuple(messages), tuple(tools), max_tokens, effort)
        self.requests.append(request)
        if not self.script:
            raise AssertionError("FakeProvider: no quedan respuestas guionizadas.")
        item = self.script.pop(0)
        if isinstance(item, LLMError):
            raise item
        if isinstance(item, LLMResponse):
            return item
        return item(request)
