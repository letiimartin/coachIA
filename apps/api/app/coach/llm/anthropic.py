"""Proveedor de Anthropic (Claude) con el SDK oficial.

- El prompt de sistema y las herramientas son estables y llevan un punto de caché; además se
  activa la caché automática del último bloque, que abarata las rondas de herramientas.
- El razonamiento de los modelos actuales va activado por defecto; su intensidad se controla
  con `effort`. Dentro de una respuesta, los bloques del asistente se reenvían tal cual
  (`provider_content`), como exige la API.
- Nunca se registra el prompt ni la clave: los errores sólo llevan el tipo y el código HTTP.
"""

from collections.abc import Sequence
from typing import Any

import anthropic

from app.coach.llm.base import (
    ChatMessage,
    LLMError,
    LLMResponse,
    LLMUsage,
    ToolCall,
    ToolSpec,
)

_CACHE = {"type": "ephemeral"}


def _content(message: ChatMessage) -> list[dict[str, Any]]:
    if message.role == "assistant" and message.provider_content is not None:
        return [
            block.model_dump(exclude_none=True) if hasattr(block, "model_dump") else block
            for block in message.provider_content
        ]
    blocks: list[dict[str, Any]] = [
        {
            "type": "tool_result",
            "tool_use_id": result.tool_call_id,
            "content": result.content,
            **({"is_error": True} if result.is_error else {}),
        }
        for result in message.tool_results
    ]
    if message.text:
        blocks.append({"type": "text", "text": message.text})
    blocks.extend(
        {"type": "tool_use", "id": call.id, "name": call.name, "input": call.input}
        for call in message.tool_calls
    )
    return blocks


def to_anthropic_messages(messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
    """Mensajes en el formato de la API. Une los turnos seguidos del mismo rol."""
    result: list[dict[str, Any]] = []
    for message in messages:
        content = _content(message)
        if not content:
            continue
        if result and result[-1]["role"] == message.role:
            result[-1]["content"].extend(content)
        else:
            result.append({"role": message.role, "content": content})
    return result


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, *, timeout_s: float = 60.0, max_retries: int = 2):
        self._client = anthropic.Anthropic(
            api_key=api_key, timeout=timeout_s, max_retries=max_retries
        )

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
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": [{"type": "text", "text": system, "cache_control": _CACHE}],
            "messages": to_anthropic_messages(messages),
            "cache_control": _CACHE,
        }
        if tools:
            params["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ]
        if effort is not None:
            params["output_config"] = {"effort": effort}
        try:
            response = self._client.messages.create(**params)
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Anthropic respondió {exc.status_code}.") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("No se ha podido conectar con Anthropic.") from exc
        except anthropic.AnthropicError as exc:
            raise LLMError(f"Error del SDK de Anthropic: {type(exc).__name__}.") from exc

        raw_usage = response.usage
        usage = LLMUsage(
            input_tokens=raw_usage.input_tokens,
            output_tokens=raw_usage.output_tokens,
            cache_read_tokens=raw_usage.cache_read_input_tokens or 0,
            cache_write_tokens=raw_usage.cache_creation_input_tokens or 0,
        )
        if response.stop_reason == "refusal":
            raise LLMError("El modelo ha rechazado la petición.", usage=usage)
        text = "".join(block.text for block in response.content if block.type == "text")
        calls = tuple(
            ToolCall(id=block.id, name=block.name, input=dict(block.input))
            for block in response.content
            if block.type == "tool_use"
        )
        return LLMResponse(
            text=text.strip(),
            tool_calls=calls,
            usage=usage,
            model=response.model,
            stop_reason=str(response.stop_reason),
            provider_content=list(response.content),
        )
