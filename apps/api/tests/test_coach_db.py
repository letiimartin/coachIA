"""Coach (#55) contra Postgres, a través de la API y con el proveedor simulado.

Nunca se llama a un LLM real. Cubre la toma de contacto, la memoria confirmada, el filtro de
seguridad, el presupuesto, el resumen, el motivo de un entreno no hecho y el aislamiento.
"""

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.coach.data import DbCoachData
from app.coach.llm.base import LLMError, LLMUsage, ToolCall
from app.coach.llm.fake import FakeProvider, FakeRequest, reply
from app.core.config import Settings
from app.core.security import TokenVerifier
from app.db.session import Database
from app.main import create_app
from app.models import (
    Activity,
    ActivitySource,
    AthleteThreshold,
    CalendarEvent,
    CoachLlmCall,
    CoachMessage,
    EventKind,
    Exercise,
    LlmCallPurpose,
    PlannedWorkout,
    Race,
    RacePriority,
    Sport,
)
from app.services import strength
from app.services.athletes import today_for
from app.services.strength import PlannedExerciseIn
from tests.conftest import (
    FakeJWKSClient,
    TokenFactory,
    database_url_for_tests,
    make_settings,
    requires_db,
)

pytestmark = requires_db

Headers = dict[str, str]


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


def _client(
    ec_private_key: ec.EllipticCurvePrivateKey, settings: Settings, provider: FakeProvider | None
) -> TestClient:
    app: FastAPI = create_app(
        settings,
        token_verifier=TokenVerifier(settings, FakeJWKSClient(ec_private_key.public_key())),
        database=Database(database_url_for_tests()),
        llm_provider=provider,
    )
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def coach_settings() -> Settings:
    return make_settings(coach_model="claude-haiku-5-5")


@pytest.fixture
def db_client(
    engine: Engine,
    ec_private_key: ec.EllipticCurvePrivateKey,
    coach_settings: Settings,
    provider: FakeProvider,
) -> Iterator[TestClient]:
    with _client(ec_private_key, coach_settings, provider) as client:
        yield client


@pytest.fixture
def headers(make_token: TokenFactory, athlete_id: uuid.UUID) -> Headers:
    return {"Authorization": f"Bearer {make_token(sub=str(athlete_id))}"}


def _usage(input_tokens: int = 2000, output_tokens: int = 200) -> LLMUsage:
    return LLMUsage(input_tokens=input_tokens, output_tokens=output_tokens, cache_read_tokens=1000)


def _chat(client: TestClient, headers: Headers) -> str:
    response = client.post("/v1/coach/conversations", headers=headers, json={"kind": "chat"})
    assert response.status_code == 201, response.text
    assert response.json()["opening"] is None
    return str(response.json()["conversation"]["id"])


def _send(client: TestClient, headers: Headers, conversation_id: str, content: str) -> Any:
    return client.post(
        f"/v1/coach/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": content},
    )


def _spend(engine: Engine, user_id: uuid.UUID, eur: str) -> None:
    with Session(engine) as session:
        session.add(
            CoachLlmCall(
                user_id=user_id,
                purpose=LlmCallPurpose.CHAT,
                provider="fake",
                model="claude-haiku-5-5",
                input_tokens=0,
                output_tokens=0,
                cost_usd=Decimal(eur),
                cost_eur=Decimal(eur),
            )
        )
        session.commit()


def _context(request: FakeRequest) -> str:
    return request.messages[0].text


# --- Estado ----------------------------------------------------------------------------------


def test_status_without_provider(
    engine: Engine, ec_private_key: ec.EllipticCurvePrivateKey, headers: Headers
) -> None:
    with _client(ec_private_key, make_settings(), None) as client:
        body = client.get("/v1/coach/status", headers=headers).json()

    assert body["available"] is False
    assert body["intake"] == {"state": "not_started", "completed_at": None, "conversation_id": None}
    assert body["budget"]["state"] == "ok"
    assert body["budget"]["limit_eur"] == 4.0
    assert body["budget"]["warning_eur"] == 3.2


def test_intake_needs_a_provider_but_safety_does_not(
    engine: Engine, ec_private_key: ec.EllipticCurvePrivateKey, headers: Headers
) -> None:
    with _client(ec_private_key, make_settings(), None) as client:
        intake = client.post("/v1/coach/conversations", headers=headers, json={})
        conversation_id = _chat(client, headers)
        normal = _send(client, headers, conversation_id, "¿Qué hago hoy?")
        red_flag = _send(client, headers, conversation_id, "Me ha dado un mareo en la bici")

    assert intake.status_code == 503
    assert intake.json()["error"]["code"] == "coach_unavailable"
    assert normal.status_code == 503
    assert red_flag.status_code == 200
    assert red_flag.json()["reply"]["origin"] == "safety_filter"


# --- Toma de contacto y memoria --------------------------------------------------------------


def test_intake_reads_data_asks_and_proposes_memory(
    db_client: TestClient, headers: Headers, provider: FakeProvider, engine: Engine
) -> None:
    provider.queue(
        reply(
            tool_calls=[
                ToolCall("t1", "get_athlete_profile", {}),
                ToolCall("t2", "get_calendar", {}),
                ToolCall("t3", "get_availability", {}),
            ],
            usage=_usage(),
        ),
        reply(
            "¡Hola! Veo que entrenas bici y trail. ¿Cuál es tu objetivo principal?", usage=_usage()
        ),
    )

    created = db_client.post("/v1/coach/conversations", headers=headers, json={})

    assert created.status_code == 201, created.text
    body = created.json()
    conversation_id = body["conversation"]["id"]
    assert body["conversation"]["kind"] == "intake"
    assert body["conversation"]["title"] == "Toma de contacto"
    opening = body["opening"]
    assert opening["user_message"] is None
    assert opening["reply"]["content"].startswith("¡Hola!")
    assert opening["reply"]["origin"] == "llm"
    assert opening["reply"]["tokens_in"] == 6000
    assert opening["reply"]["cost_eur"] > 0
    first = provider.requests[0]
    assert "toma de contacto" in first.system
    assert "Hoy:" in _context(first)
    assert "la atleta acaba de abrir" in first.messages[-1].text
    status = db_client.get("/v1/coach/status", headers=headers).json()
    assert status["intake"]["state"] == "in_progress"

    provider.queue(
        reply(
            "Resumen:\n- Objetivo: Trail de la Sierra.\n- Fuerza dos días.\n¿Lo corriges?",
            tool_calls=[
                ToolCall(
                    "t4",
                    "propose_memory",
                    {
                        "items": [
                            {"kind": "goal", "content": "Terminar el Trail de la Sierra"},
                            {"kind": "preference", "content": "Fuerza dos días por semana"},
                        ]
                    },
                )
            ],
            usage=_usage(),
        ),
        reply("Resumen:\n- Objetivo: Trail de la Sierra.\n¿Lo corriges?", usage=_usage()),
    )
    turn = _send(db_client, headers, conversation_id, "Quiero acabar el Trail de la Sierra")

    assert turn.status_code == 200, turn.text
    proposals = turn.json()["memory_proposals"]
    assert [p["status"] for p in proposals] == ["proposed", "proposed"]
    assert all(p["source_message_id"] == turn.json()["reply"]["id"] for p in proposals)
    # El coach no guarda nada: la memoria confirmada sigue vacía.
    assert db_client.get("/v1/coach/memory", headers=headers).json() == []

    goal, preference = proposals
    confirmed = db_client.post(
        f"/v1/coach/memory/{goal['id']}/confirm",
        headers=headers,
        json={"content": "Terminar el Trail de la Sierra en menos de 6 h"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["confirmed_at"] is not None
    assert db_client.get("/v1/coach/status", headers=headers).json()["intake"]["state"] == (
        "in_progress"
    )
    rejected = db_client.post(f"/v1/coach/memory/{preference['id']}/reject", headers=headers)
    assert rejected.json()["status"] == "rejected"

    status = db_client.get("/v1/coach/status", headers=headers).json()
    assert status["intake"]["state"] == "completed"
    assert status["intake"]["conversation_id"] == conversation_id
    memory = db_client.get("/v1/coach/memory", headers=headers).json()
    assert [m["content"] for m in memory] == ["Terminar el Trail de la Sierra en menos de 6 h"]

    # Con la toma de contacto hecha, la siguiente conversación es normal y lee la memoria.
    next_conversation = db_client.post("/v1/coach/conversations", headers=headers, json={})
    assert next_conversation.json()["conversation"]["kind"] == "chat"
    provider.queue(reply("Vale.", usage=_usage()))
    _send(db_client, headers, next_conversation.json()["conversation"]["id"], "Hola")
    context = _context(provider.requests[-1])
    assert "Toma de contacto: hecha." in context
    assert "(goal) Terminar el Trail de la Sierra en menos de 6 h" in context

    # Se puede repetir la toma de contacto.
    provider.queue(reply("Repasamos tus objetivos. ¿Ha cambiado algo?", usage=_usage()))
    again = db_client.post("/v1/coach/conversations", headers=headers, json={"kind": "intake"})
    assert again.json()["conversation"]["kind"] == "intake"
    status = db_client.get("/v1/coach/status", headers=headers).json()
    assert status["intake"]["state"] == "in_progress"
    assert status["intake"]["completed_at"] is not None


def test_new_proposals_supersede_pending_ones(
    db_client: TestClient, headers: Headers, provider: FakeProvider
) -> None:
    conversation_id = _chat(db_client, headers)

    def propose(content: str) -> Any:
        provider.queue(
            reply(
                tool_calls=[
                    ToolCall(
                        "p", "propose_memory", {"items": [{"kind": "goal", "content": content}]}
                    )
                ]
            ),
            reply("¿Así?"),
        )
        return _send(db_client, headers, conversation_id, "objetivo").json()["memory_proposals"]

    first = propose("Maratón de montaña")
    second = propose("Media maratón de montaña")

    pending = db_client.get("/v1/coach/memory?status=proposed", headers=headers).json()
    assert [p["id"] for p in pending] == [second[0]["id"]]
    superseded = db_client.get("/v1/coach/memory?status=superseded", headers=headers).json()
    assert [p["id"] for p in superseded] == [first[0]["id"]]
    conflict = db_client.post(
        f"/v1/coach/memory/{first[0]['id']}/confirm", headers=headers, json={}
    )
    assert conflict.status_code == 409


def test_athlete_can_add_correct_and_delete_memory(db_client: TestClient, headers: Headers) -> None:
    created = db_client.post(
        "/v1/coach/memory", headers=headers, json={"kind": "preference", "content": "Sin rodillo"}
    )
    assert created.status_code == 201
    item = created.json()
    assert (item["status"], item["source"]) == ("confirmed", "athlete")

    patched = db_client.patch(
        f"/v1/coach/memory/{item['id']}",
        headers=headers,
        json={"content": "Rodillo sólo si llueve"},
    )
    assert patched.json()["content"] == "Rodillo sólo si llueve"
    assert (
        db_client.patch(f"/v1/coach/memory/{item['id']}", headers=headers, json={}).status_code
        == 422
    )
    assert (
        db_client.post(f"/v1/coach/memory/{item['id']}/reject", headers=headers).status_code == 409
    )

    assert db_client.delete(f"/v1/coach/memory/{item['id']}", headers=headers).status_code == 204
    assert db_client.get("/v1/coach/memory", headers=headers).json() == []
    assert db_client.delete(f"/v1/coach/memory/{item['id']}", headers=headers).status_code == 404


# --- Conversación ----------------------------------------------------------------------------


def test_message_turn_is_stored_with_tools_tokens_and_cost(
    db_client: TestClient, headers: Headers, provider: FakeProvider, engine: Engine
) -> None:
    conversation_id = _chat(db_client, headers)
    provider.queue(
        reply(tool_calls=[ToolCall("t1", "get_fitness", {"days": 7})], usage=_usage(1000, 50)),
        reply("Tu forma está estable. Hoy rodaje suave.", usage=_usage(1500, 80)),
    )

    response = _send(db_client, headers, conversation_id, "  ¿Qué tal mi forma?  ")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user_message"]["role"] == "user"
    assert body["reply"]["content"] == "Tu forma está estable. Hoy rodaje suave."
    assert body["reply"]["model"] == "claude-haiku-5-5"
    assert body["reply"]["tokens_in"] == 4500  # Entrada más caché, de las dos llamadas.
    assert body["reply"]["tokens_out"] == 130
    # Haiku 5.5: (2500·0.10 + 2000·0.01 + 130·0.50) / 1e6 USD, a 1 €/USD.
    assert body["reply"]["cost_eur"] == pytest.approx(0.000335)
    assert body["budget"]["spent_eur"] == pytest.approx(0.000335)

    messages = db_client.get(f"/v1/coach/conversations/{conversation_id}/messages", headers=headers)
    assert [(m["seq"], m["role"]) for m in messages.json()] == [(1, "user"), (3, "assistant")]
    with Session(engine) as session:
        tool = session.scalars(select(CoachMessage).where(CoachMessage.seq == 2)).one()
        calls = session.scalars(select(CoachLlmCall)).all()
    assert tool.role == "tool"
    assert tool.tool_calls == [
        {"id": "t1", "name": "get_fitness", "input": {"days": 7}, "is_error": False}
    ]
    assert json.loads(tool.content)["available"] is False
    assert len(calls) == 2
    assert {str(c.message_id) for c in calls} == {body["reply"]["id"]}

    conversation = db_client.get(f"/v1/coach/conversations/{conversation_id}", headers=headers)
    assert conversation.json()["title"] == "¿Qué tal mi forma?"
    listed = db_client.get("/v1/coach/conversations", headers=headers).json()
    assert [c["id"] for c in listed] == [conversation_id]


def test_llm_error_keeps_the_cost_but_not_the_message(
    db_client: TestClient, headers: Headers, provider: FakeProvider, engine: Engine
) -> None:
    conversation_id = _chat(db_client, headers)
    provider.queue(
        reply(tool_calls=[ToolCall("t1", "get_memory", {})], usage=_usage(1000, 10)),
        LLMError("caído", usage=LLMUsage(500, 0)),
    )

    response = _send(db_client, headers, conversation_id, "Hola")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "coach_llm_error"
    assert (
        db_client.get(f"/v1/coach/conversations/{conversation_id}/messages", headers=headers).json()
        == []
    )
    with Session(engine) as session:
        tokens = session.scalars(select(CoachLlmCall.input_tokens)).all()
    assert sorted(tokens) == [500, 1000]


def test_history_window_and_summary(
    engine: Engine,
    ec_private_key: ec.EllipticCurvePrivateKey,
    headers: Headers,
    provider: FakeProvider,
) -> None:
    settings = make_settings(
        coach_model="claude-haiku-5-5", coach_history_messages=2, coach_summary_batch=2
    )
    with _client(ec_private_key, settings, provider) as client:
        conversation_id = _chat(client, headers)
        for number in range(2):
            provider.queue(reply(f"Respuesta {number}"))
            _send(client, headers, conversation_id, f"Pregunta {number}")
        # Quedan 4 mensajes: 2 fuera de la ventana → se resumen antes de responder.
        provider.queue(reply("Resumen: la atleta preguntó 0 y 1."), reply("Respuesta 2"))
        _send(client, headers, conversation_id, "Pregunta 2")
        conversation = client.get(f"/v1/coach/conversations/{conversation_id}", headers=headers)

    summary_request, answer_request = provider.requests[-2:]
    assert summary_request.tools == ()
    assert "Atleta: Pregunta 0" in summary_request.messages[0].text
    assert conversation.json()["summary"] == "Resumen: la atleta preguntó 0 y 1."
    texts = [m.text for m in answer_request.messages]
    assert "Resumen: la atleta preguntó 0 y 1." in texts[0]
    assert texts[1:] == ["Respuesta 1", "Pregunta 2"]
    with Session(engine) as session:
        purposes = session.scalars(select(CoachLlmCall.purpose)).all()
    assert purposes.count(LlmCallPurpose.SUMMARY) == 1


# --- Seguridad y presupuesto -----------------------------------------------------------------


def test_safety_filter_answers_without_calling_the_llm(
    db_client: TestClient, headers: Headers, provider: FakeProvider
) -> None:
    conversation_id = _chat(db_client, headers)

    response = _send(db_client, headers, conversation_id, "Hoy noté un dolor en el pecho al subir")

    assert response.status_code == 200
    reply_body = response.json()["reply"]
    assert reply_body["origin"] == "safety_filter"
    assert "valoración médica" in reply_body["content"]
    assert reply_body["cost_eur"] is None
    assert provider.requests == []


def test_budget_warning_and_limit(
    db_client: TestClient,
    headers: Headers,
    provider: FakeProvider,
    engine: Engine,
    athlete_id: uuid.UUID,
) -> None:
    conversation_id = _chat(db_client, headers)
    _spend(engine, athlete_id, "3.25")

    provider.queue(reply("Hola"))
    warned = _send(db_client, headers, conversation_id, "Hola")
    assert warned.json()["budget"]["state"] == "warning"
    assert db_client.get("/v1/coach/status", headers=headers).json()["budget"]["state"] == "warning"

    _spend(engine, athlete_id, "0.75")
    calls_before = len(provider.requests)
    blocked = _send(db_client, headers, conversation_id, "¿Qué hago hoy?")

    assert blocked.status_code == 200
    assert blocked.json()["reply"]["origin"] == "budget_limit"
    assert blocked.json()["budget"]["state"] == "exhausted"
    assert len(provider.requests) == calls_before


def test_budget_counts_only_the_current_month(
    db_client: TestClient, headers: Headers, engine: Engine, athlete_id: uuid.UUID
) -> None:
    with Session(engine) as session:
        session.add(
            CoachLlmCall(
                user_id=athlete_id,
                purpose=LlmCallPurpose.CHAT,
                provider="fake",
                model="m",
                input_tokens=0,
                output_tokens=0,
                cost_usd=Decimal(10),
                cost_eur=Decimal(10),
                created_at=datetime.now(UTC) - timedelta(days=40),
            )
        )
        session.commit()

    assert db_client.get("/v1/coach/status", headers=headers).json()["budget"]["state"] == "ok"


def test_budget_stops_a_turn_midway(
    db_client: TestClient,
    headers: Headers,
    provider: FakeProvider,
    engine: Engine,
    athlete_id: uuid.UUID,
) -> None:
    conversation_id = _chat(db_client, headers)
    _spend(engine, athlete_id, "3.99")
    # Una llamada muy cara agota el presupuesto: no se hace la siguiente ronda.
    provider.queue(reply(tool_calls=[ToolCall("t1", "get_memory", {})], usage=LLMUsage(200_000, 0)))

    response = _send(db_client, headers, conversation_id, "Hola")

    assert response.json()["reply"]["origin"] == "budget_limit"
    assert response.json()["reply"]["cost_eur"] > 0
    assert len(provider.requests) == 1


# --- Motivo de un entreno no hecho -----------------------------------------------------------


def _planned(engine: Engine, user_id: uuid.UUID, day: date) -> uuid.UUID:
    with Session(engine) as session:
        workout = PlannedWorkout(
            user_id=user_id, sport=Sport.RUNNING, scheduled_on=day, title="Series"
        )
        session.add(workout)
        session.commit()
        return workout.id


def test_missed_workout_reason_is_saved_and_read_back(
    db_client: TestClient,
    headers: Headers,
    provider: FakeProvider,
    engine: Engine,
    athlete_id: uuid.UUID,
) -> None:
    with Session(engine) as session:
        today = today_for(session, athlete_id)
    yesterday = _planned(engine, athlete_id, today - timedelta(days=1))
    tomorrow = _planned(engine, athlete_id, today + timedelta(days=1))
    conversation_id = _chat(db_client, headers)
    provider.queue(
        reply(
            tool_calls=[
                ToolCall(
                    "m1",
                    "record_missed_workout_reason",
                    {"workout_id": str(yesterday), "reason": "Reunión hasta tarde"},
                ),
                ToolCall(
                    "m2",
                    "record_missed_workout_reason",
                    {"workout_id": str(tomorrow), "reason": "x"},
                ),
            ]
        ),
        reply("Apuntado. Lo recolocamos."),
    )

    response = _send(db_client, headers, conversation_id, "Ayer no pude, tuve reunión hasta tarde")

    assert response.status_code == 200
    with Session(engine) as session:
        done = session.get_one(PlannedWorkout, yesterday)
        future = session.get_one(PlannedWorkout, tomorrow)
        errors = session.scalars(
            select(CoachMessage.content)
            .where(CoachMessage.role == "tool")
            .order_by(CoachMessage.seq)
        ).all()
    assert done.missed_reason == "Reunión hasta tarde"
    assert done.missed_reason_at is not None
    assert str(done.missed_reason_message_id) == response.json()["user_message"]["id"]
    assert done.status == "planned"  # No cambia el plan.
    assert future.missed_reason is None
    assert "futuro" in json.loads(errors[1])["error"]

    provider.queue(
        reply(tool_calls=[ToolCall("w", "get_planned_workouts", {})]), reply("Ya me lo contaste.")
    )
    _send(db_client, headers, conversation_id, "¿Qué tengo esta semana?")
    with Session(engine) as session:
        last_tool = session.scalars(
            select(CoachMessage.content)
            .where(CoachMessage.role == "tool")
            .order_by(CoachMessage.seq.desc())
            .limit(1)
        ).one()
    workouts = {w["id"]: w for w in json.loads(last_tool)["workouts"]}
    assert workouts[str(yesterday)]["missed_reason"] == "Reunión hasta tarde"


# --- Aislamiento -----------------------------------------------------------------------------


def test_other_athletes_data_is_not_reachable(
    db_client: TestClient,
    headers: Headers,
    provider: FakeProvider,
    engine: Engine,
    make_token: TokenFactory,
) -> None:
    other_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": other_id})
        conn.execute(text("INSERT INTO athlete_profiles (user_id) VALUES (:id)"), {"id": other_id})
    try:
        other_headers = {"Authorization": f"Bearer {make_token(sub=str(other_id))}"}
        other_conversation = _chat(db_client, other_headers)
        other_workout = _planned(engine, other_id, date(2026, 1, 1))
        other_memory = db_client.post(
            "/v1/coach/memory", headers=other_headers, json={"kind": "goal", "content": "Secreto"}
        ).json()

        assert (
            db_client.get(
                f"/v1/coach/conversations/{other_conversation}", headers=headers
            ).status_code
            == 404
        )
        assert _send(db_client, headers, other_conversation, "hola").status_code == 404
        assert (
            db_client.get(
                f"/v1/coach/conversations/{other_conversation}/messages", headers=headers
            ).status_code
            == 404
        )
        assert (
            db_client.delete(f"/v1/coach/memory/{other_memory['id']}", headers=headers).status_code
            == 404
        )

        mine = _chat(db_client, headers)
        provider.queue(
            reply(
                tool_calls=[
                    ToolCall(
                        "x",
                        "record_missed_workout_reason",
                        {"workout_id": str(other_workout), "reason": "x"},
                    ),
                    ToolCall("y", "get_memory", {}),
                ]
            ),
            reply("No lo encuentro."),
        )
        _send(db_client, headers, mine, "hola")
        with Session(engine) as session:
            results = session.scalars(
                select(CoachMessage.content)
                .where(CoachMessage.conversation_id == uuid.UUID(mine), CoachMessage.role == "tool")
                .order_by(CoachMessage.seq)
            ).all()
        assert "no encontrado" in json.loads(results[0])["error"]
        assert json.loads(results[1]) == {"confirmed": []}
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": other_id})


def test_message_validation(db_client: TestClient, headers: Headers) -> None:
    conversation_id = _chat(db_client, headers)
    assert _send(db_client, headers, conversation_id, "   ").status_code == 422
    assert _send(db_client, headers, conversation_id, "x" * 4001).status_code == 422
    assert db_client.get("/v1/coach/conversations", headers={}).status_code == 401


# --- Datos de las herramientas ---------------------------------------------------------------


def test_db_coach_data_returns_compact_summaries(
    engine: Engine, athlete_id: uuid.UUID, session: Session
) -> None:
    today = date(2026, 11, 19)
    session.add(
        AthleteThreshold(
            user_id=athlete_id,
            effective_from=date(2026, 1, 1),
            ftp_w=230,
            running_lthr_bpm=172,
            threshold_pace_s_per_km=Decimal("285.0"),
            weight_kg=Decimal("58.5"),
        )
    )
    session.add(
        Activity(
            user_id=athlete_id,
            source=ActivitySource.WAHOO,
            external_id="a1",
            sport=Sport.CYCLING,
            title="Rodaje",
            start_at=datetime(2026, 11, 18, 8, 0, tzinfo=UTC),
            elapsed_s=5400,
            distance_m=Decimal("45000"),
            load=Decimal("72.4"),
        )
    )
    event = CalendarEvent(
        user_id=athlete_id,
        kind=EventKind.RACE,
        title="Trail de la Sierra",
        start_at=datetime(2026, 12, 20, 8, 0, tzinfo=UTC),
    )
    session.add(event)
    session.flush()
    session.add(
        Race(event_id=event.id, user_id=athlete_id, priority=RacePriority.A, distance_m=42000)
    )
    session.flush()
    data = DbCoachData(session, athlete_id, today=today)

    profile = data.profile()
    assert profile["thresholds"]["ftp_w"] == 230
    assert profile["thresholds"]["threshold_pace"] == "4:45/km"
    assert profile["zones"]["cycling_power"][0].startswith("Z1")
    assert "running_pace" in profile["zones"]

    activities = data.recent_activities(14)["activities"]
    assert activities == [
        {
            "date": date(2026, 11, 18),
            "sport": Sport.CYCLING,
            "title": "Rodaje",
            "duration_min": 90,
            "distance_km": 45,
            "load": 72.4,
        }
    ]

    calendar = data.calendar(60)
    assert calendar["next_goal_race"]["title"] == "Trail de la Sierra"
    assert calendar["next_goal_race"]["days_until"] == 31
    assert calendar["next_goal_race"]["race"]["distance_km"] == 42

    assert len(data.availability()["days"]) == 7
    assert data.fitness(14) == {"today": today, "available": False}


def test_planned_strength_workouts_include_exercises_and_last_log(
    engine: Engine, athlete_id: uuid.UUID, session: Session
) -> None:
    today = date(2026, 11, 19)
    squat = session.scalars(
        select(Exercise.id).where(Exercise.slug == "back_squat", Exercise.user_id.is_(None))
    ).one()
    workout = strength.create_strength_workout(
        session,
        athlete_id,
        scheduled_on=today,
        title="Fuerza de piernas",
        exercises=[
            PlannedExerciseIn(
                squat, sets=3, target_reps=8, target_weight_kg=Decimal(60), target_rir=2
            )
        ],
        coach_reason="Base de fuerza.",
        planned_duration_s=2700,
    )
    session.flush()

    workouts = DbCoachData(session, athlete_id, today=today).planned_workouts(7, 14)["workouts"]

    assert workouts == [
        {
            "id": workout.id,
            "date": today,
            "sport": Sport.STRENGTH,
            "title": "Fuerza de piernas",
            "status": "planned",
            "planned_min": 45,
            "coach_reason": "Base de fuerza.",
            "exercises": [
                {
                    "exercise": "Sentadilla trasera",
                    "target": "3×8",
                    "target_kg": 60,
                    "target_rir": 2,
                }
            ],
        }
    ]
