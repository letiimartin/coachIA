"""Propuestas de umbral a partir del FIT de una actividad, contra Postgres (#42).

Todo con datos sintéticos: el FIT se genera en el test y la descarga va por un transporte
simulado (nunca se llama a Wahoo).
"""

import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import TokenVerifier
from app.db.session import Database
from app.integrations.wahoo.client import WahooClient
from app.main import create_app
from app.models import Activity, AthleteThreshold, DailyLoad, LoadMethod, ThresholdProposal
from tests.conftest import (
    FakeJWKSClient,
    TokenFactory,
    database_url_for_tests,
    make_settings,
    requires_db,
)
from tests.fit_builder import build_fit, steady_test

pytestmark = requires_db

Headers = dict[str, str]
URL = "/v1/athlete/threshold-proposals"
FIT_URL = "https://cdn.wahoo.test/files/test.fit"
# 08:00 UTC del 1 de marzo de 2026 = 09:00 en Madrid.
TEST_START = datetime(2026, 3, 1, 8, 0, tzinfo=UTC)


class FitServer:
    """Sirve los FIT sintéticos por URL y cuenta las descargas."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.statuses: dict[str, int] = {}
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if str(request.url) in self.statuses:
            return httpx.Response(self.statuses[str(request.url)])
        content = self.files.get(str(request.url))
        return httpx.Response(404) if content is None else httpx.Response(200, content=content)


@pytest.fixture
def fit_server() -> FitServer:
    server = FitServer()
    server.files[FIT_URL] = build_fit(steady_test(TEST_START, test_w=250))
    return server


@pytest.fixture
def db_client(
    engine: Engine, ec_private_key: ec.EllipticCurvePrivateKey, fit_server: FitServer
) -> Iterator[TestClient]:
    settings = make_settings()
    app: FastAPI = create_app(
        settings,
        token_verifier=TokenVerifier(settings, FakeJWKSClient(ec_private_key.public_key())),
        database=Database(database_url_for_tests()),
        wahoo_client=WahooClient(settings, httpx.Client(transport=httpx.MockTransport(fit_server))),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def headers(make_token: TokenFactory, athlete_id: uuid.UUID) -> Headers:
    return {"Authorization": f"Bearer {make_token(sub=str(athlete_id))}"}


def _add_activity(
    engine: Engine,
    user_id: uuid.UUID,
    *,
    sport: str = "cycling",
    url: str | None = FIT_URL,
    start_at: datetime = TEST_START,
    external_id: str | None = None,
    **values: Any,
) -> uuid.UUID:
    summary: dict[str, Any] = {"id": 1}
    if url is not None:
        summary["file"] = {"url": url}
    with Session(engine) as session:
        activity = Activity(
            user_id=user_id,
            source="wahoo",
            external_id=external_id or uuid.uuid4().hex[:12],
            sport=sport,
            start_at=start_at,
            moving_s=2700,
            elapsed_s=2700,
            raw={"id": 1, "workout_summary": summary},
            **values,
        )
        session.add(activity)
        session.commit()
        return activity.id


def _add_threshold(engine: Engine, user_id: uuid.UUID, **values: Any) -> None:
    with Session(engine) as session:
        session.add(AthleteThreshold(user_id=user_id, **values))
        session.commit()


def _thresholds(engine: Engine, user_id: uuid.UUID) -> list[AthleteThreshold]:
    with Session(engine) as session:
        return list(
            session.scalars(
                select(AthleteThreshold)
                .where(AthleteThreshold.user_id == user_id)
                .order_by(AthleteThreshold.effective_from)
            )
        )


def _create(client: TestClient, headers: Headers, activity_id: uuid.UUID) -> httpx.Response:
    return client.post(URL, headers=headers, json={"activity_id": str(activity_id)})


# --- Crear ------------------------------------------------------------------------------------


def test_create_proposal_detects_the_test_and_changes_no_threshold(
    db_client: TestClient,
    headers: Headers,
    engine: Engine,
    athlete_id: uuid.UUID,
    fit_server: FitServer,
) -> None:
    _add_threshold(engine, athlete_id, effective_from=date(2026, 1, 1), ftp_w=220)
    activity_id = _add_activity(engine, athlete_id)

    response = _create(db_client, headers, activity_id)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["protocol"] == "ftp_20min"
    assert body["activity_id"] == str(activity_id)
    assert body["test_date"] == "2026-03-01"
    assert body["proposed_ftp_w"] == 238
    assert body["interval_start_at"] == "2026-03-01T08:15:00Z"
    assert body["interval_end_at"] == "2026-03-01T08:35:00Z"
    metrics = body["metrics"]
    assert metrics["avg_power_w"] == 250.0
    assert metrics["avg_hr_bpm"] == 160.0 and metrics["max_hr_bpm"] == 160.0
    assert (metrics["start_offset_s"], metrics["end_offset_s"]) == (900, 2100)
    assert metrics["valid_data_pct"] == 100.0
    assert body["warnings"] == []
    assert body["decided_at"] is None and body["threshold_id"] is None
    # La descarga va sin el token de Wahoo y no cambia ningún umbral.
    assert len(fit_server.requests) == 1
    assert "authorization" not in fit_server.requests[0].headers
    assert [t.ftp_w for t in _thresholds(engine, athlete_id)] == [220]

    listed = db_client.get(URL, headers=headers).json()
    assert [p["id"] for p in listed] == [body["id"]]
    assert db_client.get(f"{URL}/{body['id']}", headers=headers).json() == body


def test_create_proposal_reports_quality_warnings(
    db_client: TestClient,
    headers: Headers,
    engine: Engine,
    athlete_id: uuid.UUID,
    fit_server: FitServer,
) -> None:
    url = "https://cdn.wahoo.test/files/no-warmup.fit"
    fit_server.files[url] = build_fit(steady_test(TEST_START, warmup_s=60))
    response = _create(db_client, headers, _add_activity(engine, athlete_id, url=url))
    assert response.status_code == 201, response.text
    assert [w["code"] for w in response.json()["warnings"]] == ["no_warmup"]


def test_second_pending_proposal_for_the_same_activity_conflicts(
    db_client: TestClient, headers: Headers, engine: Engine, athlete_id: uuid.UUID
) -> None:
    activity_id = _add_activity(engine, athlete_id)
    first = _create(db_client, headers, activity_id)
    assert first.status_code == 201
    assert _create(db_client, headers, activity_id).status_code == 409

    # Tras rechazarla se puede volver a analizar.
    assert db_client.post(f"{URL}/{first.json()['id']}/reject", headers=headers).status_code == 200
    assert _create(db_client, headers, activity_id).status_code == 201


SHORT_FIT = build_fit(steady_test(TEST_START, warmup_s=0, test_s=600, cooldown_s=0))
NO_POWER_FIT = build_fit([replace(r, power_w=None) for r in steady_test(TEST_START)])


@pytest.mark.parametrize(
    ("fit", "code"),
    [
        (b"no es un FIT", "fit_invalid"),
        (SHORT_FIT, "test_too_short"),
        (NO_POWER_FIT, "no_power_data"),
    ],
)
def test_create_proposal_rejects_unusable_files(
    db_client: TestClient,
    headers: Headers,
    engine: Engine,
    athlete_id: uuid.UUID,
    fit_server: FitServer,
    fit: bytes,
    code: str,
) -> None:
    url = f"https://cdn.wahoo.test/files/{code}.fit"
    fit_server.files[url] = fit
    response = _create(db_client, headers, _add_activity(engine, athlete_id, url=url))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert db_client.get(URL, headers=headers).json() == []


def test_create_proposal_requires_a_cycling_activity_with_fit(
    db_client: TestClient,
    headers: Headers,
    engine: Engine,
    athlete_id: uuid.UUID,
    fit_server: FitServer,
) -> None:
    running = _add_activity(engine, athlete_id, sport="running")
    without_file = _add_activity(engine, athlete_id, url=None)
    missing_file = _add_activity(engine, athlete_id, url="https://cdn.wahoo.test/files/gone.fit")

    assert _create(db_client, headers, running).json()["error"]["code"] == "not_cycling"
    assert _create(db_client, headers, without_file).json()["error"]["code"] == "fit_unavailable"
    gone = _create(db_client, headers, missing_file)
    assert gone.status_code == 422
    assert gone.json()["error"]["code"] == "fit_unavailable"
    assert _create(db_client, headers, uuid.uuid4()).status_code == 404


def test_wahoo_errors_while_downloading_map_to_502(
    db_client: TestClient,
    headers: Headers,
    engine: Engine,
    athlete_id: uuid.UUID,
    fit_server: FitServer,
) -> None:
    url = "https://cdn.wahoo.test/files/error.fit"
    fit_server.statuses[url] = 503
    response = _create(db_client, headers, _add_activity(engine, athlete_id, url=url))
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "bad_gateway"


# --- Aceptar y rechazar -----------------------------------------------------------------------


def test_accept_creates_a_test_threshold_copying_the_current_values(
    db_client: TestClient, headers: Headers, engine: Engine, athlete_id: uuid.UUID
) -> None:
    _add_threshold(
        engine,
        athlete_id,
        effective_from=date(2026, 1, 1),
        ftp_w=220,
        cycling_lthr_bpm=165,
        running_lthr_bpm=172,
        hr_max_bpm=186,
        hr_rest_bpm=48,
        threshold_pace_s_per_km=Decimal("285.0"),
        weight_kg=Decimal("58.50"),
    )
    # Umbral posterior al test: no es el vigente el día del test, no se copia.
    _add_threshold(engine, athlete_id, effective_from=date(2026, 6, 1), ftp_w=240, hr_max_bpm=190)
    proposal_id = _create(db_client, headers, _add_activity(engine, athlete_id)).json()["id"]

    response = db_client.post(f"{URL}/{proposal_id}/accept", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "accepted"
    assert body["decided_at"] is not None
    rows = _thresholds(engine, athlete_id)
    assert [r.effective_from for r in rows] == [
        date(2026, 1, 1),
        date(2026, 3, 1),
        date(2026, 6, 1),
    ]
    new = rows[1]
    assert str(new.id) == body["threshold_id"]
    assert new.source == "test"
    assert new.ftp_w == 238
    assert (new.cycling_lthr_bpm, new.running_lthr_bpm) == (165, 172)
    assert (new.hr_max_bpm, new.hr_rest_bpm) == (186, 48)
    assert new.threshold_pace_s_per_km == Decimal("285.0")
    assert new.weight_kg == Decimal("58.50")
    assert new.legacy_lthr_bpm is None
    assert proposal_id in (new.notes or "")

    again = db_client.post(f"{URL}/{proposal_id}/accept", headers=headers)
    assert again.status_code == 409
    assert db_client.post(f"{URL}/{proposal_id}/reject", headers=headers).status_code == 409


def test_accept_without_previous_thresholds_only_sets_ftp(
    db_client: TestClient, headers: Headers, engine: Engine, athlete_id: uuid.UUID
) -> None:
    proposal_id = _create(db_client, headers, _add_activity(engine, athlete_id)).json()["id"]
    assert db_client.post(f"{URL}/{proposal_id}/accept", headers=headers).status_code == 200
    [row] = _thresholds(engine, athlete_id)
    assert (row.effective_from, row.ftp_w, row.source) == (date(2026, 3, 1), 238, "test")
    assert row.hr_max_bpm is None and row.cycling_lthr_bpm is None


def test_accept_keeps_existing_loads_and_only_fills_missing_ones(
    db_client: TestClient, headers: Headers, engine: Engine, athlete_id: uuid.UUID
) -> None:
    _add_threshold(engine, athlete_id, effective_from=date(2026, 1, 1), ftp_w=200)
    later = TEST_START + timedelta(days=3)
    with_load = _add_activity(
        engine,
        athlete_id,
        start_at=later,
        url=None,
        normalized_power_w=200,
        load=Decimal("75.0"),
        load_method=LoadMethod.POWER,
        intensity_factor=Decimal("1.000"),
    )
    without_load = _add_activity(
        engine, athlete_id, start_at=later + timedelta(days=1), url=None, normalized_power_w=238
    )
    proposal_id = _create(db_client, headers, _add_activity(engine, athlete_id)).json()["id"]

    assert db_client.post(f"{URL}/{proposal_id}/accept", headers=headers).status_code == 200

    with Session(engine) as session:
        kept = session.get_one(Activity, with_load)
        filled = session.get_one(Activity, without_load)
        # La carga existente no cambia aunque el FTP vigente sea otro (protección de #22).
        assert (kept.load, kept.load_method) == (Decimal("75.0"), LoadMethod.POWER)
        # La que faltaba se calcula con el FTP nuevo: 45 min a NP = FTP → 75.
        assert filled.load == Decimal("75.0")
        assert filled.intensity_factor == Decimal("1.000")
        assert session.scalar(select(DailyLoad).where(DailyLoad.user_id == athlete_id))


def test_accept_conflicts_with_a_threshold_on_the_same_day(
    db_client: TestClient, headers: Headers, engine: Engine, athlete_id: uuid.UUID
) -> None:
    proposal_id = _create(db_client, headers, _add_activity(engine, athlete_id)).json()["id"]
    _add_threshold(engine, athlete_id, effective_from=date(2026, 3, 1), ftp_w=210)

    response = db_client.post(f"{URL}/{proposal_id}/accept", headers=headers)

    assert response.status_code == 409
    assert [t.ftp_w for t in _thresholds(engine, athlete_id)] == [210]
    assert db_client.get(f"{URL}/{proposal_id}", headers=headers).json()["status"] == "pending"


def test_reject_changes_nothing_else(
    db_client: TestClient, headers: Headers, engine: Engine, athlete_id: uuid.UUID
) -> None:
    _add_threshold(engine, athlete_id, effective_from=date(2026, 1, 1), ftp_w=220)
    proposal_id = _create(db_client, headers, _add_activity(engine, athlete_id)).json()["id"]

    response = db_client.post(f"{URL}/{proposal_id}/reject", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["threshold_id"] is None
    assert [t.ftp_w for t in _thresholds(engine, athlete_id)] == [220]
    assert db_client.post(f"{URL}/{proposal_id}/accept", headers=headers).status_code == 409
    pending = db_client.get(URL, headers=headers, params={"status": "pending"}).json()
    assert pending == []
    rejected = db_client.get(URL, headers=headers, params={"status": "rejected"}).json()
    assert [p["id"] for p in rejected] == [proposal_id]


def test_proposals_of_other_athletes_are_not_visible(
    db_client: TestClient,
    headers: Headers,
    engine: Engine,
    athlete_id: uuid.UUID,
    make_token: TokenFactory,
) -> None:
    activity_id = _add_activity(engine, athlete_id)
    proposal_id = _create(db_client, headers, activity_id).json()["id"]
    other = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": other})
    try:
        other_headers = {"Authorization": f"Bearer {make_token(sub=str(other))}"}
        assert db_client.get(URL, headers=other_headers).json() == []
        assert db_client.get(f"{URL}/{proposal_id}", headers=other_headers).status_code == 404
        for action in ("accept", "reject"):
            response = db_client.post(f"{URL}/{proposal_id}/{action}", headers=other_headers)
            assert response.status_code == 404
        assert _create(db_client, other_headers, activity_id).status_code == 404
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": other})


# --- Esquema ----------------------------------------------------------------------------------


def _proposal(user_id: uuid.UUID, activity_id: uuid.UUID, **values: Any) -> ThresholdProposal:
    defaults: dict[str, Any] = {
        "user_id": user_id,
        "activity_id": activity_id,
        "protocol": "ftp_20min",
        "test_date": date(2026, 3, 1),
        "interval_start_at": TEST_START,
        "interval_end_at": TEST_START + timedelta(minutes=20),
        "proposed_ftp_w": 238,
    }
    return ThresholdProposal(**{**defaults, **values})


@pytest.mark.parametrize(
    "values",
    [
        {"proposed_ftp_w": 20},
        {"interval_end_at": TEST_START},
        {"status": "accepted"},  # decidida sin decided_at
        {"decided_at": TEST_START},  # pendiente con decided_at
        {"protocol": "otro"},
    ],
)
def test_check_constraints(engine: Engine, athlete_id: uuid.UUID, values: dict[str, Any]) -> None:
    activity_id = _add_activity(engine, athlete_id)
    with Session(engine) as session:
        session.add(_proposal(athlete_id, activity_id, **values))
        with pytest.raises((IntegrityError, LookupError)):
            session.commit()


def test_only_one_pending_proposal_per_activity(engine: Engine, athlete_id: uuid.UUID) -> None:
    activity_id = _add_activity(engine, athlete_id)
    with Session(engine) as session:
        session.add(_proposal(athlete_id, activity_id))
        session.add(_proposal(athlete_id, activity_id, status="rejected", decided_at=TEST_START))
        session.commit()
        session.add(_proposal(athlete_id, activity_id))
        with pytest.raises(IntegrityError):
            session.commit()


def test_proposals_are_deleted_with_the_activity(engine: Engine, athlete_id: uuid.UUID) -> None:
    activity_id = _add_activity(engine, athlete_id)
    with Session(engine) as session:
        session.add(_proposal(athlete_id, activity_id))
        session.commit()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM activities WHERE id = :id"), {"id": activity_id})
        remaining = conn.execute(
            text("SELECT count(*) FROM threshold_proposals WHERE user_id = :id"),
            {"id": athlete_id},
        ).scalar()
    assert remaining == 0
