"""El set de evaluación del coach (#55) es válido y el script funciona sin llamar a un LLM.

El CI no ejecuta la evaluación real (necesita claves): sólo comprueba el set y el informe con
el proveedor simulado.
"""

from app.coach.safety import check_message
from app.coach.tools import TOOL_NAMES
from evals.coach_eval import (
    DEFAULT_MODELS,
    PLANNER_ACTIONS,
    dry_run_provider,
    evaluate,
    invented_numbers,
    load_cases,
    parse_proposal,
    render_report,
)


def test_case_set_is_valid() -> None:
    document = load_cases()
    cases = document["cases"]

    assert 18 <= len(cases) <= 24
    assert len({c["id"] for c in cases}) == len(cases)
    categories = {c["category"] for c in cases}
    assert {"toma_de_contacto", "forma", "que_hago_hoy", "bandera_roja", "adaptacion"} <= categories
    assert sum(c["mode"] == "planner" for c in cases) >= 5
    for case in cases:
        assert case["mode"] in {"chat", "intake_opening", "planner"}
        assert case["rubric"] and case["description"]
        expect = case["expect"]
        for group in expect.get("tools_any", []):
            assert set(group) <= set(TOOL_NAMES), case["id"]
        assert set(expect.get("actions", [])) <= PLANNER_ACTIONS
        users = [m["content"] for m in case.get("conversation", []) if m["role"] == "user"]
        if "safety_filter" in expect:
            # Las expectativas del set coinciden con el filtro determinista.
            assert check_message(users[-1]).triggered == expect["safety_filter"], case["id"]


def test_dry_run_evaluates_every_case_and_reports_cost() -> None:
    runs = evaluate(DEFAULT_MODELS, dry_run_provider())
    report = render_report(runs, DEFAULT_MODELS, dry_run=True, effort="low")

    assert len(runs) == len(load_cases()["cases"]) * len(DEFAULT_MODELS)
    assert all(r.error is None for r in runs)
    safety = [r for r in runs if r.case_id == "roja_dolor_pecho"]
    assert all(r.llm_calls == 0 and r.checks == {"safety_filter": True} for r in safety)
    haiku = sum(r.cost_usd for r in runs if r.model == "claude-haiku-5-5")
    opus = sum(r.cost_usd for r in runs if r.model == "claude-opus-5-5")
    assert 0 < haiku < opus
    assert "SIMULACRO" in report
    assert "platform.claude.com/docs/en/about-claude/pricing" in report
    for model in DEFAULT_MODELS:
        assert f"`{model}`" in report


def test_invented_numbers_flags_only_unsupported_figures() -> None:
    sources = ['{"ctl":58.3,"tsb":-5.8,"ftp_w":230}', "Tengo 60 minutos"]

    assert invented_numbers("CTL 58,3, TSB −5,8, FTP 230 W, 60 min y 3 series", sources) == []
    assert invented_numbers("Tu TSS de ayer fue 87,5 y tu CTL 61", sources) == ["61", "87.5"]


def test_parse_proposal_extracts_the_json_object() -> None:
    assert parse_proposal('Aquí va: {"action": "keep"} fin') == {"action": "keep"}
    assert parse_proposal("sin json") is None
    assert parse_proposal("{no es json}") is None
