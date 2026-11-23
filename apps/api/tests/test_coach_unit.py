"""Coach (#55) sin BD: filtro de seguridad, coste, herramientas, bucle y proveedor de Anthropic.

Nunca se llama a un LLM real: el proveedor simulado da respuestas guionizadas y el cliente de
Anthropic se sustituye por un doble.
"""

import json
import uuid
from decimal import Decimal
from typing import Any

import anthropic
import httpx2
import pytest

from app.coach import prompts
from app.coach.budget import call_cost_usd, to_eur
from app.coach.engine import FINAL_ROUND_HINT, NO_ANSWER_REPLY, run_turn
from app.coach.llm.anthropic import AnthropicProvider, to_anthropic_messages
from app.coach.llm.base import ChatMessage, LLMError, LLMUsage, ToolCall, ToolResult
from app.coach.llm.fake import FakeProvider, reply
from app.coach.safety import RedFlag, check_message
from app.coach.tools import TOOL_NAMES, TOOL_SPECS, MemoryProposal, dumps, execute
from app.core.config import DEFAULT_LLM_PRICES, ModelPrice
from app.core.errors import NotFoundError
from tests.conftest import make_settings

# --- Filtro de seguridad ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "flag"),
    [
        ("Hoy subiendo el puerto he notado un dolor en el pecho", RedFlag.CHEST_PAIN),
        ("Me duele mucho el pecho al respirar", RedFlag.CHEST_PAIN),
        ("Sentí una opresión en el pecho", RedFlag.CHEST_PAIN),
        ("He tenido palpitaciones en las series", RedFlag.CHEST_PAIN),
        ("Me mareé al terminar las series", RedFlag.DIZZINESS),
        ("estoy MAREADA desde esta mañana", RedFlag.DIZZINESS),
        ("Casi me desmayo en la cuesta", RedFlag.FAINTING),
        ("Perdí el conocimiento un momento", RedFlag.FAINTING),
        ("Creo que tengo un esguince de tobillo", RedFlag.ACUTE_INJURY),
        ("Me he roto la muñeca al caerme", RedFlag.ACUTE_INJURY),
        ("No puedo apoyar el pie desde la bajada", RedFlag.ACUTE_INJURY),
        ("Noté un chasquido en el gemelo", RedFlag.ACUTE_INJURY),
    ],
)
def test_safety_filter_detects_red_flags(text: str, flag: RedFlag) -> None:
    assert flag in check_message(text).flags


@pytest.mark.parametrize(
    "text",
    [
        "Hoy estoy muy cansada",
        "¿Qué hago hoy? Tengo una hora",
        "Me duelen un poco las piernas de ayer",
        "La subida al puerto fue durísima",
        "Mañana voy a la playa, con la marea baja",
        "Me roto los turnos con mi pareja para entrenar",
    ],
)
def test_safety_filter_lets_normal_messages_through(text: str) -> None:
    assert not check_message(text).triggered


def test_safety_filter_is_conservative_with_negations() -> None:
    # Deliberado: mejor un aviso de más que uno de menos.
    assert check_message("No me duele el pecho, tranquilo").triggered


# --- Coste -----------------------------------------------------------------------------------


def test_call_cost_uses_official_prices_per_token_type() -> None:
    price = ModelPrice(
        input=Decimal(2), output=Decimal(10), cache_write=Decimal("2.5"), cache_read=Decimal("0.1")
    )
    usage = LLMUsage(
        input_tokens=1000, output_tokens=500, cache_read_tokens=10_000, cache_write_tokens=2000
    )
    # (1000·2 + 500·10 + 2000·2.5 + 10000·0.1) / 1e6
    assert call_cost_usd(price, usage) == Decimal("0.013000")


def test_long_context_multiplier_applies_over_the_threshold() -> None:
    price = DEFAULT_LLM_PRICES["claude-haiku-5-5"]
    short = LLMUsage(input_tokens=100_000, output_tokens=0)
    long = LLMUsage(input_tokens=60_000, output_tokens=0, cache_read_tokens=40_001)

    assert call_cost_usd(price, short) == Decimal("0.010000")
    # Todo el prompt (con la caché) cuenta para el umbral, y el recargo es para todo.
    assert call_cost_usd(price, long) == Decimal("0.032000")


def test_cost_in_euros_uses_the_configured_rate() -> None:
    settings = make_settings(coach_usd_to_eur="0.9")
    assert to_eur(settings, Decimal("0.010000")) == Decimal("0.009000")


def test_default_settings_price_the_default_model() -> None:
    settings = make_settings()
    assert settings.coach_model in settings.coach_llm_prices
    assert settings.coach_monthly_budget_eur == Decimal("4.00")
    assert settings.coach_budget_warning_ratio == Decimal("0.8")


def test_prices_can_be_configured_as_json() -> None:
    settings = make_settings(
        coach_llm_prices={"m": {"input": 1, "output": 2, "cache_write": 1, "cache_read": 0.1}}
    )
    assert settings.coach_llm_prices["m"].output == Decimal(2)


# --- Herramientas ----------------------------------------------------------------------------


class FixtureData:
    """`CoachData` simulado: devuelve lo que se le da y guarda las escrituras."""

    def __init__(self) -> None:
        self.proposed: list[MemoryProposal] = []
        self.missed: list[tuple[uuid.UUID, str]] = []

    def profile(self) -> dict[str, Any]:
        return {"profile": {"name": "Leti"}, "thresholds": {"ftp_w": 230}}

    def fitness(self, days: int) -> dict[str, Any]:
        return {"ctl": 55.2, "atl": 61.0, "tsb": -5.8, "days": days}

    def recent_activities(self, days: int) -> dict[str, Any]:
        return {"activities": [], "days": days}

    def calendar(self, days_ahead: int) -> dict[str, Any]:
        return {"events": [], "days_ahead": days_ahead}

    def planned_workouts(self, days_back: int, days_ahead: int) -> dict[str, Any]:
        return {"workouts": [], "back": days_back, "ahead": days_ahead}

    def availability(self) -> dict[str, Any]:
        return {"days": []}

    def memory(self) -> dict[str, Any]:
        return {"confirmed": []}

    def propose_memory(self, items: list[MemoryProposal]) -> dict[str, Any]:
        self.proposed.extend(items)
        return {"proposed": len(items)}

    def record_missed_reason(self, workout_id: uuid.UUID, reason: str) -> dict[str, Any]:
        if workout_id == uuid.UUID(int=0):
            raise NotFoundError("Entreno planificado no encontrado.")
        self.missed.append((workout_id, reason))
        return {"saved": True}


def test_tool_specs_are_valid_schemas_without_athlete_ids() -> None:
    assert len(TOOL_SPECS) == len(set(TOOL_NAMES)) == 9
    for spec in TOOL_SPECS:
        assert spec.input_schema["type"] == "object"
        assert spec.description
        # Ninguna herramienta permite elegir la atleta: siempre es la de la sesión.
        assert not {"user_id", "athlete_id"} & set(spec.input_schema["properties"])


def test_execute_validates_input_and_dispatches() -> None:
    data = FixtureData()

    result = execute(data, ToolCall("1", "get_fitness", {"days": 7}))
    assert not result.is_error
    assert json.loads(result.content)["days"] == 7

    default = execute(data, ToolCall("2", "get_planned_workouts", {}))
    assert json.loads(default.content) == {"workouts": [], "back": 7, "ahead": 14}

    for name in ("get_athlete_profile", "get_availability", "get_memory", "get_calendar"):
        assert not execute(data, ToolCall("x", name, {})).is_error


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("get_fitness", {"days": 1000}),
        ("get_fitness", {"user_id": "otra"}),
        ("propose_memory", {"items": []}),
        ("record_missed_workout_reason", {"workout_id": "no-es-un-uuid", "reason": "x"}),
        ("drop_table", {}),
    ],
)
def test_execute_returns_errors_to_the_model(name: str, args: dict[str, Any]) -> None:
    result = execute(FixtureData(), ToolCall("1", name, args))
    assert result.is_error
    assert "error" in json.loads(result.content)


def test_execute_turns_business_errors_into_tool_errors() -> None:
    result = execute(
        FixtureData(),
        ToolCall(
            "1",
            "record_missed_workout_reason",
            {"workout_id": str(uuid.UUID(int=0)), "reason": "x"},
        ),
    )
    assert result.is_error
    assert json.loads(result.content) == {"error": "Entreno planificado no encontrado."}


def test_dumps_is_compact_and_deterministic() -> None:
    assert dumps({"b": 1, "a": "ñ"}) == '{"a":"ñ","b":1}'


def test_system_prompt_is_stable() -> None:
    # Sin fechas ni datos de la atleta: así se cachea junto con las herramientas.
    chat = prompts.system_prompt(intake=False)
    intake = prompts.system_prompt(intake=True)
    assert intake.startswith(chat)
    assert "toma de contacto" in intake
    assert "2026" not in chat


# --- Bucle de una respuesta ------------------------------------------------------------------


def _run(provider: FakeProvider, *, max_rounds: int = 3, budget: list[bool] | None = None) -> Any:
    calls: list[LLMUsage] = []
    budget_answers = list(budget or [])
    result = run_turn(
        provider=provider,
        model="fake-model",
        system="sistema",
        messages=[ChatMessage(role="user", text="hola")],
        tools=TOOL_SPECS,
        data=FixtureData(),
        max_rounds=max_rounds,
        max_tokens=500,
        effort="low",
        on_call=calls.append,
        has_budget=lambda: budget_answers.pop(0) if budget_answers else True,
    )
    return result, calls


def test_run_turn_executes_tools_until_the_model_answers() -> None:
    provider = FakeProvider()
    provider.queue(
        reply(tool_calls=[ToolCall("t1", "get_fitness", {}), ToolCall("t2", "get_memory", {})]),
        reply("Tu TSB es -5.8: puedes hacer el rodaje."),
    )

    result, calls = _run(provider)

    assert result.text == "Tu TSB es -5.8: puedes hacer el rodaje."
    assert [step.call.name for step in result.steps] == ["get_fitness", "get_memory"]
    assert result.llm_calls == len(calls) == 2
    assert result.usage.input_tokens == 2000
    second = provider.requests[1].messages
    assert second[-1].tool_results[0].tool_call_id == "t1"
    assert second[-2].tool_calls[1].name == "get_memory"
    assert provider.requests[0].effort == "low"


def test_run_turn_forces_an_answer_after_the_last_round() -> None:
    provider = FakeProvider()
    provider.queue(
        reply(tool_calls=[ToolCall("t1", "get_fitness", {})]),
        reply("Respondo ya.", tool_calls=[ToolCall("t2", "get_fitness", {})]),
    )

    result, _ = _run(provider, max_rounds=1)

    assert result.text == "Respondo ya."
    assert provider.requests[-1].messages[-1].text == FINAL_ROUND_HINT


def test_run_turn_without_text_gives_a_safe_answer() -> None:
    provider = FakeProvider()
    provider.queue(reply(""))
    result, _ = _run(provider)
    assert result.text == NO_ANSWER_REPLY


def test_run_turn_stops_when_the_budget_runs_out() -> None:
    provider = FakeProvider()
    provider.queue(reply(tool_calls=[ToolCall("t1", "get_fitness", {})]))

    result, calls = _run(provider, budget=[False])

    assert result.stopped_by_budget
    assert len(calls) == 1
    assert provider.script == []


def test_run_turn_propagates_provider_errors() -> None:
    provider = FakeProvider()
    provider.queue(LLMError("caído"))
    with pytest.raises(LLMError):
        _run(provider)


# --- Proveedor de Anthropic (sin red) --------------------------------------------------------


def test_messages_are_translated_and_same_roles_merged() -> None:
    messages = [
        ChatMessage(role="user", text="contexto"),
        ChatMessage(role="user", text="hola"),
        ChatMessage(role="assistant", text="miro", tool_calls=(ToolCall("t1", "get_memory", {}),)),
        ChatMessage(role="user", tool_results=(ToolResult("t1", "{}", is_error=True),)),
    ]

    result = to_anthropic_messages(messages)

    assert [m["role"] for m in result] == ["user", "assistant", "user"]
    assert [b["text"] for b in result[0]["content"]] == ["contexto", "hola"]
    assert result[1]["content"][1] == {
        "type": "tool_use",
        "id": "t1",
        "name": "get_memory",
        "input": {},
    }
    assert result[2]["content"][0]["is_error"] is True


class _FakeMessages:
    def __init__(self, response: Any = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.params: dict[str, Any] = {}

    def create(self, **params: Any) -> Any:
        self.params = params
        if self.error is not None:
            raise self.error
        return self.response


class _FakeClient:
    def __init__(self, messages: _FakeMessages):
        self.messages = messages


def _message(
    content: list[dict[str, Any]], stop_reason: str = "end_turn"
) -> anthropic.types.Message:
    return anthropic.types.Message.model_validate(
        {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "claude-haiku-5-5",
            "content": content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {
                "input_tokens": 120,
                "output_tokens": 40,
                "cache_read_input_tokens": 3000,
                "cache_creation_input_tokens": 0,
            },
        }
    )


def _provider(messages: _FakeMessages) -> AnthropicProvider:
    provider = AnthropicProvider("sk-test")
    provider._client = _FakeClient(messages)  # type: ignore[assignment]
    return provider


def test_anthropic_provider_sends_cached_system_tools_and_effort() -> None:
    fake = _FakeMessages(
        _message(
            [
                {"type": "text", "text": "Miro tus datos."},
                {"type": "tool_use", "id": "tu_1", "name": "get_fitness", "input": {"days": 7}},
            ],
            stop_reason="tool_use",
        )
    )

    response = _provider(fake).complete(
        model="claude-haiku-5-5",
        system="sistema",
        messages=[ChatMessage(role="user", text="hola")],
        tools=TOOL_SPECS[:1],
        max_tokens=800,
        effort="low",
    )

    assert fake.params["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert fake.params["cache_control"] == {"type": "ephemeral"}
    assert fake.params["output_config"] == {"effort": "low"}
    assert fake.params["tools"][0]["name"] == TOOL_SPECS[0].name
    assert response.tool_calls == (ToolCall("tu_1", "get_fitness", {"days": 7}),)
    assert response.usage == LLMUsage(120, 40, 3000, 0)
    # Dentro de la misma respuesta se reenvía el contenido original.
    replay = to_anthropic_messages([response.as_message()])
    assert replay[0]["content"][1]["type"] == "tool_use"


def test_anthropic_provider_maps_errors_without_leaking_details() -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.APIConnectionError(request=request)

    with pytest.raises(LLMError, match="No se ha podido conectar"):
        _provider(_FakeMessages(error=error)).complete(
            model="m", system="s", messages=[], tools=(), max_tokens=10
        )


def test_anthropic_refusal_is_an_error_with_usage() -> None:
    fake = _FakeMessages(_message([], stop_reason="refusal"))
    with pytest.raises(LLMError) as info:
        _provider(fake).complete(model="m", system="s", messages=[], tools=(), max_tokens=10)
    assert info.value.usage == LLMUsage(120, 40, 3000, 0)
