"""Evaluación de modelos para el coach (#55). No la ejecuta el CI.

Ejecuta el set de `evals/coach/cases.json` contra 2-3 modelos candidatos con el bucle real del
coach (`app.coach.engine`) y herramientas simuladas, y escribe un informe con la calidad por
criterio, los tokens y el coste con los precios oficiales (`DEFAULT_LLM_PRICES`).

Uso (desde `apps/api`):
    ANTHROPIC_API_KEY=... uv run python -m evals.coach_eval \\
        --models claude-haiku-5-5,claude-sonnet-5-5,claude-opus-5-5
    uv run python -m evals.coach_eval --dry-run     # sin clave: respuestas simuladas
"""

import argparse
import copy
import json
import os
import re
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.coach import prompts
from app.coach.budget import call_cost_usd
from app.coach.engine import run_turn
from app.coach.llm.base import ChatMessage, LLMError, LLMProvider, LLMResponse, LLMUsage
from app.coach.llm.fake import FakeProvider, FakeRequest
from app.coach.safety import SAFETY_REPLY, check_message
from app.coach.tools import TOOL_SPECS, MemoryProposal, dumps
from app.core.config import DEFAULT_LLM_PRICES, ModelPrice
from app.core.text import search_key

EVAL_DIR = Path(__file__).resolve().parent / "coach"
CASES_PATH = EVAL_DIR / "cases.json"
PLANNER_PROMPT = EVAL_DIR / "planner.md"
DEFAULT_MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")
PRICES_SOURCE = (
    "https://platform.claude.com/docs/en/about-claude/pricing (consultado el 19/11/2026)"
)
PLANNER_ACTIONS = {
    "keep",
    "reduce_intensity",
    "reduce_volume",
    "swap_recovery",
    "move",
    "remove",
    "create",
}
WRITE_TOOLS = {"propose_memory", "record_missed_workout_reason"}
# Uso previsto para proyectar el coste mensual (doc. de arquitectura, 12.3).
CHAT_CALLS_PER_MONTH = 15 * 30
PLANNER_CALLS_PER_MONTH = 4
_NUMBER = re.compile(r"(?<![\w/])[-−]?\d+(?:[.,]\d+)?")

# --- Datos simulados -------------------------------------------------------------------------


def load_cases(path: Path = CASES_PATH) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return document


def case_context(document: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    context = copy.deepcopy(document["base_context"])
    context.update(copy.deepcopy(case.get("context", {})))
    return context


class FixtureCoachData:
    """`CoachData` con los datos simulados del caso; las escrituras se guardan en memoria."""

    def __init__(self, context: dict[str, Any]):
        self.context = context
        self.proposed: list[dict[str, str]] = []
        self.missed: list[dict[str, str]] = []

    def profile(self) -> dict[str, Any]:
        return dict(self.context["profile"])

    def fitness(self, days: int) -> dict[str, Any]:
        return dict(self.context["fitness"])

    def recent_activities(self, days: int) -> dict[str, Any]:
        return dict(self.context["activities"])

    def calendar(self, days_ahead: int) -> dict[str, Any]:
        return dict(self.context["calendar"])

    def planned_workouts(self, days_back: int, days_ahead: int) -> dict[str, Any]:
        return dict(self.context["planned_workouts"])

    def availability(self) -> dict[str, Any]:
        return dict(self.context["availability"])

    def memory(self) -> dict[str, Any]:
        return dict(self.context["memory"])

    def propose_memory(self, items: list[MemoryProposal]) -> dict[str, Any]:
        self.proposed = [{"kind": i.kind.value, "content": i.content} for i in items]
        return {"proposed": len(items), "status": "pendiente de que la atleta lo confirme"}

    def record_missed_reason(self, workout_id: uuid.UUID, reason: str) -> dict[str, Any]:
        self.missed.append({"workout_id": str(workout_id), "reason": reason})
        return {"saved": True, "workout_id": str(workout_id)}


def context_message(context: dict[str, Any], intake: bool) -> ChatMessage:
    """El mismo formato que el primer mensaje del orquestador."""
    memory = context["memory"]["confirmed"]
    lines = [
        "[Contexto del sistema; no es un mensaje de la atleta]",
        f"- Hoy: {context['today']}, Europe/Madrid.",
        "- Conversación: " + ("toma de contacto." if intake else "normal."),
        "- Toma de contacto: " + ("pendiente." if intake else "hecha."),
    ]
    if memory:
        lines.append("- Memoria confirmada:")
        lines.extend(f"  - ({m['kind']}) {m['content']}" for m in memory)
    else:
        lines.append("- Memoria confirmada: ninguna todavía.")
    return ChatMessage(role="user", text="\n".join(lines))


# --- Evaluación ------------------------------------------------------------------------------


@dataclass
class CaseRun:
    case_id: str
    category: str
    mode: str
    model: str
    text: str = ""
    tools: list[str] = field(default_factory=list)
    usage: LLMUsage = field(default_factory=LLMUsage)
    llm_calls: int = 0
    cost_usd: Decimal = Decimal(0)
    checks: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def score(self) -> float:
        return sum(self.checks.values()) / len(self.checks) if self.checks else 0.0


def _contains(text: str, needle: str) -> bool:
    return search_key(needle) in search_key(text) or needle.lower() in text.lower()


def _numbers(text: str) -> set[str]:
    return {m.group().replace(",", ".").replace("−", "-") for m in _NUMBER.finditer(text)}


def invented_numbers(reply: str, sources: Sequence[str]) -> list[str]:
    """Cifras de la respuesta con decimales o ≥ 30 que no están en los datos ni en la charla."""
    allowed: set[str] = set()
    for source in sources:
        for number in _numbers(source):
            allowed.update({number, number.lstrip("-")})
            if "." in number:
                allowed.add(number.rstrip("0").rstrip("."))
    suspicious = []
    for number in sorted(_numbers(reply)):
        plain = number.lstrip("-")
        if "." not in plain and float(plain) < 30:
            continue
        if number not in allowed and plain not in allowed:
            suspicious.append(number)
    return suspicious


def parse_proposal(text: str) -> dict[str, Any] | None:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def score_case(case: dict[str, Any], run: CaseRun, sources: Sequence[str], safety: bool) -> None:
    expect = case.get("expect", {})
    if "safety_filter" in expect:
        run.checks["safety_filter"] = safety == expect["safety_filter"]
    if safety:
        return
    for group in expect.get("tools_any", []):
        run.checks[f"tools:{'|'.join(group)}"] = any(name in run.tools for name in group)
    if case["mode"] == "planner":
        proposal = parse_proposal(run.text)
        required = {"action", "changes", "rationale", "message_to_athlete"}
        run.checks["json"] = proposal is not None and required <= proposal.keys()
        action = None if proposal is None else proposal.get("action")
        run.checks["action"] = action in set(expect.get("actions", PLANNER_ACTIONS))
        visible = "" if proposal is None else f"{proposal.get('message_to_athlete', '')}"
    else:
        visible = run.text
        if "max_questions" in expect:
            run.checks["max_questions"] = run.text.count("?") <= expect["max_questions"]
    for index, group in enumerate(expect.get("include", [])):
        target = run.text if case["mode"] == "planner" else visible
        run.checks[f"include:{index}"] = any(_contains(target, needle) for needle in group)
    if expect.get("exclude"):
        run.checks["exclude"] = not any(_contains(visible, n) for n in expect["exclude"])
    invented = invented_numbers(run.text, sources)
    run.checks["no_invented_numbers"] = not invented
    if invented:
        run.notes.append(f"Cifras no encontradas en los datos: {', '.join(invented)}")


def run_case(
    document: dict[str, Any],
    case: dict[str, Any],
    provider: LLMProvider,
    model: str,
    price: ModelPrice,
    effort: str | None,
) -> CaseRun:
    run = CaseRun(case["id"], case["category"], case["mode"], model)
    context = case_context(document, case)
    conversation = case.get("conversation", [])
    last_user = next((m["content"] for m in reversed(conversation) if m["role"] == "user"), "")
    safety = check_message(last_user).triggered if last_user else False
    sources = [dumps(context), *(m["content"] for m in conversation)]
    if safety:
        run.text = SAFETY_REPLY
        score_case(case, run, sources, safety)
        return run

    intake = bool(case.get("intake"))
    planner = case["mode"] == "planner"
    messages = [context_message(context, intake)]
    messages.extend(
        ChatMessage(role="user" if m["role"] == "user" else "assistant", text=m["content"])
        for m in conversation
    )
    if case["mode"] == "intake_opening":
        messages.append(
            ChatMessage(
                role="user", text="(Sistema: la atleta acaba de abrir la toma de contacto.)"
            )
        )
    system = (
        PLANNER_PROMPT.read_text(encoding="utf-8").strip()
        if planner
        else prompts.system_prompt(intake=intake)
    )
    tools = [t for t in TOOL_SPECS if not (planner and t.name in WRITE_TOOLS)]
    data = FixtureCoachData(context)
    costs: list[Decimal] = []
    try:
        turn = run_turn(
            provider=provider,
            model=model,
            system=system,
            messages=messages,
            tools=tools,
            data=data,
            max_rounds=5,
            max_tokens=2000,
            effort=effort,
            on_call=lambda usage: costs.append(call_cost_usd(price, usage)),
            has_budget=lambda: True,
        )
    except LLMError as exc:
        run.error = str(exc)
        run.cost_usd = sum(costs, Decimal(0))
        return run
    run.text = turn.text
    run.tools = [step.call.name for step in turn.steps]
    run.usage = turn.usage
    run.llm_calls = turn.llm_calls
    run.cost_usd = sum(costs, Decimal(0))
    sources.extend(step.result.content for step in turn.steps)
    score_case(case, run, sources, safety)
    if data.proposed:
        run.notes.append(f"Memoria propuesta: {json.dumps(data.proposed, ensure_ascii=False)}")
    if data.missed:
        run.notes.append(f"Motivos guardados: {json.dumps(data.missed, ensure_ascii=False)}")
    return run


# --- Informe ---------------------------------------------------------------------------------


def _mean(values: Sequence[float | Decimal]) -> float:
    return (
        float(sum(values, Decimal(0)) if values and isinstance(values[0], Decimal) else sum(values))
        / len(values)
        if values
        else 0.0
    )  # type: ignore[arg-type]


def summary_rows(runs: Sequence[CaseRun], models: Sequence[str]) -> list[dict[str, Any]]:
    rows = []
    for model in models:
        mine = [r for r in runs if r.model == model]
        llm = [r for r in mine if r.llm_calls]
        chat = [r for r in llm if r.mode != "planner"]
        planner = [r for r in llm if r.mode == "planner"]
        chat_cost = _mean([float(r.cost_usd) for r in chat])
        planner_cost = _mean([float(r.cost_usd) for r in planner])
        rows.append(
            {
                "model": model,
                "quality": _mean([r.score for r in mine]),
                "quality_chat": _mean([r.score for r in mine if r.mode != "planner"]),
                "quality_planner": _mean([r.score for r in mine if r.mode == "planner"]),
                "errors": sum(1 for r in mine if r.error),
                "input_tokens": _mean([float(r.usage.prompt_tokens) for r in llm]),
                "output_tokens": _mean([float(r.usage.output_tokens) for r in llm]),
                "cost_chat_usd": chat_cost,
                "cost_planner_usd": planner_cost,
                "total_cost_usd": float(sum((r.cost_usd for r in mine), Decimal(0))),
                "monthly_usd": chat_cost * CHAT_CALLS_PER_MONTH
                + planner_cost * PLANNER_CALLS_PER_MONTH,
            }
        )
    return rows


def render_report(
    runs: Sequence[CaseRun], models: Sequence[str], *, dry_run: bool, effort: str | None
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Evaluación del coach",
        "",
        f"- Fecha: {now}{' — **SIMULACRO** (respuestas simuladas, sin LLM)' if dry_run else ''}",
        f"- Modelos: {', '.join(models)} · effort: {effort or 'por defecto'}",
        f"- Precios oficiales (USD/MTok): {PRICES_SOURCE}",
        f"- Proyección mensual: {CHAT_CALLS_PER_MONTH} mensajes de chat y "
        f"{PLANNER_CALLS_PER_MONTH} propuestas al mes.",
        "",
        "## Resumen",
        "",
        "| Modelo | Calidad | Chat | Propuestas | Errores | Tokens entrada/caso | Tokens salida/caso "
        "| USD/mensaje chat | USD/propuesta | USD esta pasada | USD/mes estimado |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in summary_rows(runs, models):
        lines.append(
            f"| `{row['model']}` | {row['quality']:.0%} | {row['quality_chat']:.0%} "
            f"| {row['quality_planner']:.0%} | {row['errors']} | {row['input_tokens']:.0f} "
            f"| {row['output_tokens']:.0f} | {row['cost_chat_usd']:.5f} "
            f"| {row['cost_planner_usd']:.5f} | {row['total_cost_usd']:.4f} "
            f"| {row['monthly_usd']:.2f} |"
        )
    lines += ["", "## Casos", ""]
    by_case: dict[str, list[CaseRun]] = {}
    for run in runs:
        by_case.setdefault(run.case_id, []).append(run)
    for case_id, case_runs in by_case.items():
        first = case_runs[0]
        lines += [f"### `{case_id}` ({first.category}, {first.mode})", ""]
        for run in case_runs:
            failed = [name for name, ok in run.checks.items() if not ok]
            lines.append(
                f"**{run.model}** · {run.score:.0%} · {run.usage.prompt_tokens} in / "
                f"{run.usage.output_tokens} out · {run.cost_usd:.5f} USD · herramientas: "
                f"{', '.join(run.tools) or '—'}"
                + (f" · falla: {', '.join(failed)}" if failed else "")
            )
            if run.error:
                lines.append(f"> Error: {run.error}")
            for note in run.notes:
                lines.append(f"> {note}")
            lines += ["", "```text", run.text.strip() or "(sin texto)", "```", ""]
    return "\n".join(lines) + "\n"


# --- Ejecución -------------------------------------------------------------------------------


def dry_run_provider() -> FakeProvider:
    """Respuestas simuladas: consulta una herramienta y responde un texto fijo."""

    def answer(request: FakeRequest) -> LLMResponse:
        if request.tools and not any(m.tool_results for m in request.messages):
            from app.coach.llm.base import ToolCall

            name = request.tools[0].name
            return LLMResponse(
                "", (ToolCall("dry", name, {}),), LLMUsage(800, 20), request.model, "tool_use"
            )
        text = '{"action": "keep", "changes": [], "rationale": "simulado", "message_to_athlete": "Simulado."}'
        if "JSON" not in request.system:
            text = "Respuesta simulada. ¿Te encaja?"
        return LLMResponse(text, (), LLMUsage(1000, 60, 500, 0), request.model, "end_turn")

    provider = FakeProvider()
    provider.script = [answer] * 10_000
    return provider


def evaluate(
    models: Sequence[str],
    provider: LLMProvider,
    *,
    case_ids: Sequence[str] = (),
    repeat: int = 1,
    effort: str | None = "low",
    prices: dict[str, ModelPrice] | None = None,
) -> list[CaseRun]:
    document = load_cases()
    prices = prices or DEFAULT_LLM_PRICES
    cases = [c for c in document["cases"] if not case_ids or c["id"] in case_ids]
    runs = []
    for model in models:
        if model not in prices:
            raise SystemExit(f"No hay precio oficial configurado para {model}.")
        for case in cases:
            for _ in range(repeat):
                runs.append(run_case(document, case, provider, model, prices[model], effort))
                print(f"{model} · {case['id']}: {runs[-1].score:.0%}", file=sys.stderr)
    return runs


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--cases", default="", help="Ids separados por comas (por defecto, todos).")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--effort", default="low", choices=["low", "medium", "high", "none"])
    parser.add_argument("--dry-run", action="store_true", help="Sin LLM: respuestas simuladas.")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    effort = None if args.effort == "none" else args.effort
    provider: LLMProvider
    if args.dry_run:
        provider = dry_run_provider()
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise SystemExit("Falta ANTHROPIC_API_KEY (o usa --dry-run).")
        from app.coach.llm.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key)

    runs = evaluate(
        models,
        provider,
        case_ids=[c for c in args.cases.split(",") if c],
        repeat=args.repeat,
        effort=effort,
    )
    report = render_report(runs, models, dry_run=args.dry_run, effort=effort)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    out = args.out or EVAL_DIR / "results" / f"{stamp}{'-dry-run' if args.dry_run else ''}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"Informe escrito en {out}")


if __name__ == "__main__":
    main()
