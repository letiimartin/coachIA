"""Proveedores de LLM intercambiables (`LLMProvider`)."""

from app.coach.llm.base import (
    ChatMessage,
    LLMError,
    LLMProvider,
    LLMResponse,
    LLMUsage,
    ToolCall,
    ToolResult,
    ToolSpec,
)

__all__ = [
    "ChatMessage",
    "LLMError",
    "LLMProvider",
    "LLMResponse",
    "LLMUsage",
    "ToolCall",
    "ToolResult",
    "ToolSpec",
]
