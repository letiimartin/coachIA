"""El bucle de una respuesta: LLM → herramientas → LLM, hasta que responde con texto.

No sabe nada de la BD: recibe el proveedor, los mensajes, los datos de las herramientas y dos
funciones del orquestador, una para registrar cada llamada (coste) y otra que dice si queda
presupuesto antes de la siguiente. Lo usan el orquestador y la evaluación de modelos.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from app.coach.llm.base import ChatMessage, LLMProvider, LLMUsage, ToolCall, ToolResult, ToolSpec
from app.coach.tools import CoachData, execute

FINAL_ROUND_HINT = (
    "(Sistema: has llegado al máximo de consultas a las herramientas. Responde ya a la atleta "
    "con lo que tienes.)"
)
NO_ANSWER_REPLY = (
    "Ahora mismo no he podido preparar una respuesta completa. ¿Me lo puedes preguntar de "
    "nuevo, quizá de forma más concreta?"
)


@dataclass(frozen=True, slots=True)
class ToolStep:
    call: ToolCall
    result: ToolResult


@dataclass
class TurnResult:
    text: str
    model: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    steps: list[ToolStep] = field(default_factory=list)
    llm_calls: int = 0
    stopped_by_budget: bool = False


def run_turn(
    *,
    provider: LLMProvider,
    model: str,
    system: str,
    messages: Sequence[ChatMessage],
    tools: Sequence[ToolSpec],
    data: CoachData,
    max_rounds: int,
    max_tokens: int,
    effort: str | None,
    on_call: Callable[[LLMUsage], None],
    has_budget: Callable[[], bool],
) -> TurnResult:
    """Ejecuta una respuesta. `LLMError` se propaga (tras registrar lo consumido)."""
    conversation = list(messages)
    result = TurnResult(text="", model=model)
    for round_number in range(max_rounds + 1):
        if result.llm_calls and not has_budget():
            result.stopped_by_budget = True
            return result
        last_round = round_number == max_rounds
        if last_round:
            conversation.append(ChatMessage(role="user", text=FINAL_ROUND_HINT))
        response = provider.complete(
            model=model,
            system=system,
            messages=conversation,
            tools=tools,
            max_tokens=max_tokens,
            effort=effort,
        )
        result.llm_calls += 1
        result.usage = result.usage + response.usage
        on_call(response.usage)
        if not response.tool_calls or last_round:
            result.text = response.text or NO_ANSWER_REPLY
            return result
        conversation.append(response.as_message())
        tool_results = []
        for call in response.tool_calls:
            tool_result = execute(data, call)
            result.steps.append(ToolStep(call, tool_result))
            tool_results.append(tool_result)
        conversation.append(ChatMessage(role="user", tool_results=tuple(tool_results)))
    raise AssertionError("unreachable")  # pragma: no cover
