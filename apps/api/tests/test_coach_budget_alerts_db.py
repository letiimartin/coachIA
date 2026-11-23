"""Avisos de gasto del LLM a los desarrolladores (#61): endpoint interno para n8n.

El canal (email por n8n) se simula: el test hace lo que hace el workflow, leer los avisos
pendientes y confirmar su envío.
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.coach.llm.fake import FakeProvider, reply
from app.core.security import TokenVerifier
from app.db.session import Database
from app.main import create_app
from app.models import CoachBudgetAlert, CoachLlmCall, LlmCallPurpose
from tests.conftest import (
    INTERNAL_KEY,
    FakeJWKSClient,
    TokenFactory,
    database_url_for_tests,
    make_settings,
    requires_db,
)

pytestmark = requires_db

INTERNAL = {"X-Internal-API-Key": INTERNAL_KEY}


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def client(
    engine: Engine, ec_private_key: ec.EllipticCurvePrivateKey, provider: FakeProvider
) -> Iterator[TestClient]:
    settings = make_settings(coach_model="claude-haiku-5-5")
    app = create_app(
        settings,
        token_verifier=TokenVerifier(settings, FakeJWKSClient(ec_private_key.public_key())),
        database=Database(database_url_for_tests()),
        llm_provider=provider,
    )
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _clean_calls(engine: Engine) -> Iterator[None]:
    # Los avisos miran a todas las atletas: cada test empieza sin llamadas de otros tests.
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM coach_budget_alerts"))
        conn.execute(text("DELETE FROM coach_llm_calls"))
    yield


def _spend(
    engine: Engine,
    user_id: uuid.UUID,
    eur: str,
    model: str = "claude-haiku-5-5",
    created_at: datetime | None = None,
) -> None:
    with Session(engine) as session:
        call = CoachLlmCall(
            user_id=user_id,
            purpose=LlmCallPurpose.CHAT,
            provider="fake",
            model=model,
            input_tokens=0,
            output_tokens=0,
            cost_usd=Decimal(eur),
            cost_eur=Decimal(eur),
        )
        if created_at is not None:
            call.created_at = created_at
        session.add(call)
        session.commit()


def _alerts(client: TestClient) -> list[dict[str, Any]]:
    response = client.get("/internal/coach/budget-alerts", headers=INTERNAL)
    assert response.status_code == 200, response.text
    alerts: list[dict[str, Any]] = response.json()["alerts"]
    return alerts


def _sent(client: TestClient, keys: list[str]) -> dict[str, Any]:
    response = client.post(
        "/internal/coach/budget-alerts/sent", headers=INTERNAL, json={"keys": keys}
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_requires_the_internal_key(client: TestClient) -> None:
    assert client.get("/internal/coach/budget-alerts").status_code == 401
    assert (
        client.post("/internal/coach/budget-alerts/sent", json={"keys": ["x"]}).status_code == 401
    )


def test_no_alerts_below_the_warning(
    client: TestClient, engine: Engine, athlete_id: uuid.UUID
) -> None:
    _spend(engine, athlete_id, "3.19")
    assert _alerts(client) == []


def test_warning_and_limit_are_sent_once_per_threshold(
    client: TestClient, engine: Engine, athlete_id: uuid.UUID
) -> None:
    _spend(engine, athlete_id, "2.00")
    _spend(engine, athlete_id, "1.00")
    _spend(engine, athlete_id, "0.30", model="claude-sonnet-5-5")

    [warning] = _alerts(client)
    month = datetime.now(UTC).date().replace(day=1).isoformat()
    assert warning["key"] == f"{athlete_id}:{month}:warning"
    assert warning["threshold"] == "warning"
    assert warning["month"] == month
    assert warning["spent_eur"] == pytest.approx(3.3)
    assert warning["limit_eur"] == 4.0
    assert warning["threshold_eur"] == 3.2
    assert warning["percent"] == 83
    assert warning["calls"] == 3
    assert warning["by_model"] == [
        {"model": "claude-haiku-5-5", "calls": 2, "cost_eur": 3.0},
        {"model": "claude-sonnet-5-5", "calls": 1, "cost_eur": 0.3},
    ]
    assert "83 %" in warning["subject"]
    for fragment in ("3.30 € de 4.00 €", "Llamadas al LLM: 3", "claude-sonnet-5-5: 1 llamadas"):
        assert fragment in warning["text"]

    # Hasta que n8n confirma el envío, el aviso sigue pendiente.
    assert [a["key"] for a in _alerts(client)] == [warning["key"]]
    assert _sent(client, [warning["key"]]) == {"recorded": 1, "ignored": 0}
    assert _alerts(client) == []
    # Confirmarlo otra vez no hace nada.
    assert _sent(client, [warning["key"]]) == {"recorded": 0, "ignored": 1}

    # Al llegar al 100 %, un aviso nuevo (y sólo ese).
    _spend(engine, athlete_id, "0.70")
    [limit] = _alerts(client)
    assert limit["threshold"] == "limit"
    assert limit["percent"] == 100
    assert "límite alcanzado" in limit["subject"]
    assert _sent(client, [limit["key"]]) == {"recorded": 1, "ignored": 0}

    _spend(engine, athlete_id, "1.00")
    assert _alerts(client) == []
    with Session(engine) as session:
        rows = session.scalars(select(CoachBudgetAlert).order_by(CoachBudgetAlert.sent_at)).all()
        assert [(r.threshold.value, r.spent_eur) for r in rows] == [
            ("warning", Decimal("3.3")),
            ("limit", Decimal("4.0")),
        ]


def test_jumping_past_the_limit_gives_both_alerts(
    client: TestClient, engine: Engine, athlete_id: uuid.UUID
) -> None:
    _spend(engine, athlete_id, "4.50")
    alerts = _alerts(client)
    assert [a["threshold"] for a in alerts] == ["warning", "limit"]
    assert _sent(client, [a["key"] for a in alerts]) == {"recorded": 2, "ignored": 0}
    assert _alerts(client) == []


def test_only_pending_alerts_can_be_marked_as_sent(
    client: TestClient, engine: Engine, athlete_id: uuid.UUID
) -> None:
    month = datetime.now(UTC).date().replace(day=1).isoformat()
    _spend(engine, athlete_id, "3.50")
    # El 100 % aún no se ha cruzado: confirmarlo no puede silenciar el aviso futuro.
    outcome = _sent(client, [f"{athlete_id}:{month}:limit", "inventada"])
    assert outcome == {"recorded": 0, "ignored": 2}
    _spend(engine, athlete_id, "0.50")
    assert [a["threshold"] for a in _alerts(client)] == ["warning", "limit"]


def test_previous_months_do_not_count(
    client: TestClient, engine: Engine, athlete_id: uuid.UUID
) -> None:
    _spend(engine, athlete_id, "10", created_at=datetime.now(UTC) - timedelta(days=40))
    assert _alerts(client) == []


def test_alerts_are_per_athlete_and_carry_no_conversation_content(
    client: TestClient,
    engine: Engine,
    athlete_id: uuid.UUID,
    provider: FakeProvider,
    make_token: TokenFactory,
) -> None:
    other = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": other})
        conn.execute(text("INSERT INTO athlete_profiles (user_id) VALUES (:id)"), {"id": other})
    try:
        headers = {"Authorization": f"Bearer {make_token(sub=str(athlete_id))}"}
        conversation = client.post(
            "/v1/coach/conversations", headers=headers, json={"kind": "chat"}
        ).json()["conversation"]["id"]
        _spend(engine, athlete_id, "3.50")
        provider.queue(reply("Respuesta secreta del coach"))
        client.post(
            f"/v1/coach/conversations/{conversation}/messages",
            headers=headers,
            json={"content": "Quiero preparar el trail de Penyagolosa"},
        )
        _spend(engine, other, "1.00")

        alerts = _alerts(client)
        assert [a["user_id"] for a in alerts] == [str(athlete_id)]
        dump = str(alerts)
        assert "Penyagolosa" not in dump
        assert "secreta" not in dump
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": other})


def test_alerts_follow_the_athletes_month(
    client: TestClient, engine: Engine, athlete_id: uuid.UUID
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE athlete_profiles SET timezone = 'Pacific/Kiritimati' WHERE user_id = :id"),
            {"id": athlete_id},
        )
    _spend(engine, athlete_id, "3.50")
    [alert] = _alerts(client)
    local_month = datetime.now(ZoneInfo("Pacific/Kiritimati")).date().replace(day=1)
    assert alert["month"] == local_month.isoformat()
