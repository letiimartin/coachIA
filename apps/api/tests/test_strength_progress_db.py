"""Rendimiento de fuerza (#33) contra Postgres: resumen semanal y progresión por ejercicio."""

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.core.security import TokenVerifier
from app.db.session import Database
from app.main import create_app
from app.models import Activity, ActivitySource, Sport, StrengthSetLog
from app.services import strength
from tests.conftest import (
    FakeJWKSClient,
    TokenFactory,
    database_url_for_tests,
    make_settings,
    requires_db,
)
from tests.test_strength_db import (
    Headers,
    _complete,
    _exercise_id,
    _planned_ids,
    _put_sets,
    _workout,
)

pytestmark = requires_db


@pytest.fixture
def db_client(engine: Engine, ec_private_key: ec.EllipticCurvePrivateKey) -> Iterator[TestClient]:
    settings = make_settings()
    app: FastAPI = create_app(
        settings,
        token_verifier=TokenVerifier(settings, FakeJWKSClient(ec_private_key.public_key())),
        database=Database(database_url_for_tests()),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def headers(make_token: TokenFactory, athlete_id: uuid.UUID) -> Headers:
    return {"Authorization": f"Bearer {make_token(sub=str(athlete_id))}"}


def _done_session(
    engine: Engine,
    client: TestClient,
    headers: Headers,
    user_id: uuid.UUID,
    *,
    day: date,
    started_at: str,
    squat: list[tuple[int, float]],
    plank: tuple[int, ...] = (),
    duration_s: int = 3000,
    rpe: int | None = 7,
    incomplete: tuple[int, float] | None = None,
) -> uuid.UUID:
    """Sesión completada con series de sentadilla (repeticiones, peso) y de plancha (s)."""
    workout_id = _workout(engine, user_id, scheduled_on=day)
    squat_id, plank_id = _planned_ids(client, headers, workout_id)
    sets: list[dict[str, Any]] = [
        {"planned_exercise_id": squat_id, "set_number": n, "reps": reps, "weight_kg": weight}
        for n, (reps, weight) in enumerate(squat, start=1)
    ]
    if incomplete is not None:
        reps, weight = incomplete
        sets.append(
            {
                "planned_exercise_id": squat_id,
                "set_number": len(squat) + 1,
                "reps": reps,
                "weight_kg": weight,
                "completed": False,
            }
        )
    sets += [
        {"planned_exercise_id": plank_id, "set_number": n, "seconds": seconds}
        for n, seconds in enumerate(plank, start=1)
    ]
    assert _put_sets(client, headers, workout_id, sets).status_code == 200
    response = _complete(
        client, headers, workout_id, started_at=started_at, duration_s=duration_s, rpe=rpe
    )
    assert response.status_code == 200, response.text
    return workout_id


# --- Resumen semanal -------------------------------------------------------------------------


def test_weekly_summary(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    # Semana del 2 nov: una sesión de 50 min con RPE 7 (350) y otra de 40 min con RPE 6 (240).
    _done_session(
        engine,
        db_client,
        headers,
        athlete_id,
        day=date(2026, 11, 3),
        started_at="2026-11-03T18:00:00+01:00",
        squat=[(8, 60)],
    )
    _done_session(
        engine,
        db_client,
        headers,
        athlete_id,
        day=date(2026, 11, 8),
        # Domingo a las 23:30 en Madrid (22:30 UTC): sigue siendo la semana del 2 nov.
        started_at="2026-11-08T23:30:00+01:00",
        squat=[(8, 60)],
        duration_s=2400,
        rpe=6,
    )
    # Lunes 16 a las 00:30 en Madrid (domingo 15 en UTC): semana del 16, sin RPE ni carga.
    _done_session(
        engine,
        db_client,
        headers,
        athlete_id,
        day=date(2026, 11, 16),
        started_at="2026-11-16T00:30:00+01:00",
        squat=[(8, 60)],
        duration_s=1800,
        rpe=None,
    )
    # No cuentan: una sesión sin completar y una actividad de fuerza marcada como duplicada.
    pending = _workout(engine, athlete_id, scheduled_on=date(2026, 11, 17))
    with Session(engine) as session:
        original = session.scalars(
            select(Activity.id).where(Activity.user_id == athlete_id).limit(1)
        ).one()
        session.add(
            Activity(
                user_id=athlete_id,
                source=ActivitySource.STRAVA,
                external_id="dup-1",
                sport=Sport.STRENGTH,
                start_at=datetime(2026, 11, 17, 17, 0, tzinfo=UTC),
                elapsed_s=3600,
                duplicate_of_id=original,
            )
        )
        session.commit()
    assert pending is not None

    response = db_client.get(
        "/v1/strength/weekly", headers=headers, params={"from": "2026-10-28", "to": "2026-11-19"}
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["from"], body["to"]) == ("2026-10-28", "2026-11-19")
    assert body["weeks"] == [
        {
            "week_start": "2026-10-26",
            "sessions": 0,
            "duration_s": 0,
            "load": 0.0,
            "sessions_without_load": 0,
        },
        {
            "week_start": "2026-11-02",
            "sessions": 2,
            "duration_s": 5400,
            "load": 590.0,
            "sessions_without_load": 0,
        },
        {
            "week_start": "2026-11-09",
            "sessions": 0,
            "duration_s": 0,
            "load": 0.0,
            "sessions_without_load": 0,
        },
        {
            "week_start": "2026-11-16",
            "sessions": 1,
            "duration_s": 1800,
            "load": 0.0,
            "sessions_without_load": 1,
        },
    ]

    # La fuerza nunca se suma a la forma: CTL/ATL/TSB siguen a 0.
    fitness = db_client.get(
        "/v1/athlete/fitness", headers=headers, params={"from": "2026-11-01", "to": "2026-11-19"}
    ).json()
    assert all((d["load"], d["ctl"], d["atl"]) == (0, 0, 0) for d in fitness["days"])


def test_weekly_summary_without_strength(db_client: TestClient, headers: Headers) -> None:
    response = db_client.get(
        "/v1/strength/weekly", headers=headers, params={"from": "2026-11-19", "to": "2026-11-19"}
    )

    assert response.json()["weeks"] == [
        {
            "week_start": "2026-11-16",
            "sessions": 0,
            "duration_s": 0,
            "load": 0.0,
            "sessions_without_load": 0,
        }
    ]


def test_weekly_summary_validates_the_range(db_client: TestClient, headers: Headers) -> None:
    for params in (
        {"from": "2026-11-19", "to": "2026-11-01"},
        {"from": "2025-01-01", "to": "2026-11-19"},
        {"from": "2026-11-19"},
    ):
        response = db_client.get("/v1/strength/weekly", headers=headers, params=params)
        assert response.status_code == 422, params


def test_weekly_summary_is_per_athlete(
    engine: Engine,
    db_client: TestClient,
    headers: Headers,
    make_token: TokenFactory,
    athlete_id: uuid.UUID,
) -> None:
    _done_session(
        engine,
        db_client,
        headers,
        athlete_id,
        day=date(2026, 11, 17),
        started_at="2026-11-17T18:00:00+01:00",
        squat=[(8, 60)],
    )
    other = {"Authorization": f"Bearer {make_token(sub=str(uuid.uuid4()))}"}

    weeks = db_client.get(
        "/v1/strength/weekly", headers=other, params={"from": "2026-11-17", "to": "2026-11-17"}
    ).json()["weeks"]

    assert weeks[0]["sessions"] == 0
    assert db_client.get("/v1/strength/progress", headers=other).json() == []


# --- Progresión por ejercicio ----------------------------------------------------------------


def test_exercise_progress(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    squat = _exercise_id(engine, "back_squat")
    first = _done_session(
        engine,
        db_client,
        headers,
        athlete_id,
        day=date(2026, 11, 3),
        started_at="2026-11-03T18:00:00+01:00",
        squat=[(8, 55), (8, 57.5), (8, 57.5)],
        plank=(45, 45),
    )
    _done_session(
        engine,
        db_client,
        headers,
        athlete_id,
        day=date(2026, 11, 17),
        started_at="2026-11-17T18:00:00+01:00",
        squat=[(8, 60), (6, 62.5)],
        # Una serie no hecha no cuenta, aunque tenga más peso.
        incomplete=(3, 70),
        plank=(60,),
    )
    # Una actividad de fuerza sin plan (sincronizada) con series también cuenta.
    with Session(engine) as session:
        activity = Activity(
            user_id=athlete_id,
            source=ActivitySource.MANUAL,
            sport=Sport.STRENGTH,
            start_at=datetime(2026, 11, 10, 17, 0, tzinfo=UTC),
            elapsed_s=1800,
        )
        session.add(activity)
        session.flush()
        session.add_all(
            StrengthSetLog(
                user_id=athlete_id,
                activity_id=activity.id,
                exercise_id=squat,
                set_number=n,
                reps=reps,
                weight_kg=Decimal(weight),
            )
            for n, (reps, weight) in enumerate([(10, "50"), (10, "50")], start=1)
        )
        session.commit()
        unplanned = activity.id
    # Una sesión sin completar no cuenta.
    pending = _workout(engine, athlete_id, scheduled_on=date(2026, 11, 19))
    pending_squat, _ = _planned_ids(db_client, headers, pending)
    _put_sets(
        db_client,
        headers,
        pending,
        [{"planned_exercise_id": pending_squat, "set_number": 1, "reps": 8, "weight_kg": 80}],
    )

    response = db_client.get(f"/v1/strength/exercises/{squat}/progress", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["exercise"]["slug"] == "back_squat"
    sessions = body["sessions"]
    assert [s["performed_on"] for s in sessions] == ["2026-11-03", "2026-11-10", "2026-11-17"]
    assert sessions[0]["planned_workout_id"] == str(first)
    assert (sessions[1]["activity_id"], sessions[1]["planned_workout_id"]) == (
        str(unplanned),
        None,
    )
    assert {
        key: sessions[0][key]
        for key in (
            "sets",
            "total_reps",
            "total_seconds",
            "max_weight_kg",
            "volume_kg",
            "best_set_reps",
            "best_set_seconds",
        )
    } == {
        "sets": 3,
        "total_reps": 24,
        "total_seconds": None,
        "max_weight_kg": 57.5,
        "volume_kg": 1360.0,  # 8×55 + 8×57,5 + 8×57,5
        "best_set_reps": 8,
        "best_set_seconds": None,
    }
    assert (sessions[1]["max_weight_kg"], sessions[1]["volume_kg"]) == (50.0, 1000.0)
    last = sessions[2]
    assert (last["sets"], last["total_reps"], last["max_weight_kg"]) == (2, 14, 62.5)
    assert (last["volume_kg"], last["best_set_reps"]) == (855.0, 6)

    plank = _exercise_id(engine, "plank")
    plank_sessions = db_client.get(
        f"/v1/strength/exercises/{plank}/progress", headers=headers
    ).json()["sessions"]
    assert [(s["sets"], s["total_seconds"], s["best_set_seconds"]) for s in plank_sessions] == [
        (2, 90, 45),
        (1, 60, 60),
    ]
    assert all(s["volume_kg"] is None and s["total_reps"] is None for s in plank_sessions)

    performed = db_client.get("/v1/strength/progress", headers=headers).json()
    assert [
        (
            p["exercise"]["slug"],
            p["sessions"],
            p["first_performed_on"],
            p["last_performed_on"],
            p["last_max_weight_kg"],
        )
        for p in performed
    ] == [
        # Mismo último día: por nombre («Plancha» antes que «Sentadilla trasera»).
        ("plank", 2, "2026-11-03", "2026-11-17", None),
        ("back_squat", 3, "2026-11-03", "2026-11-17", 62.5),
    ]


def test_exercise_without_history(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    squat = _exercise_id(engine, "back_squat")

    response = db_client.get(f"/v1/strength/exercises/{squat}/progress", headers=headers)

    assert response.status_code == 200
    assert response.json()["sessions"] == []
    assert db_client.get("/v1/strength/progress", headers=headers).json() == []


def test_progress_of_unknown_or_foreign_exercise(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    other = uuid.uuid4()
    with Session(engine) as session:
        session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": other})
        foreign = strength.create_exercise(
            session,
            other,
            slug="sled_pull",
            name="Arrastre de trineo",
            muscle_group=strength.MuscleGroup.FULL_BODY,
            mode=strength.ExerciseMode.SECONDS,
        ).id
        session.commit()
    try:
        for exercise_id in (uuid.uuid4(), foreign):
            response = db_client.get(
                f"/v1/strength/exercises/{exercise_id}/progress", headers=headers
            )
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "not_found"
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": other})
