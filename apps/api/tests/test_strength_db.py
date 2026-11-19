"""Fuerza (#30) contra Postgres: catálogo, sesiones, registro de series, completar y historial."""

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import TokenVerifier
from app.db.session import Database
from app.main import create_app
from app.models import (
    Activity,
    DailyLoad,
    Exercise,
    ExerciseMode,
    ExerciseOrigin,
    LoadMethod,
    MuscleGroup,
    PlannedWorkout,
    PlannedWorkoutStatus,
    Sport,
    StrengthSetLog,
)
from app.services import strength
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
DAY = date(2026, 11, 19)
# 18:30 en Madrid.
STARTED_AT = "2026-11-19T18:30:00+01:00"


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


def _exercise_id(engine: Engine, slug: str) -> uuid.UUID:
    with Session(engine) as session:
        return session.scalars(
            select(Exercise.id).where(Exercise.slug == slug, Exercise.user_id.is_(None))
        ).one()


def _workout(
    engine: Engine,
    user_id: uuid.UUID,
    *,
    scheduled_on: date = DAY,
    title: str = "Fuerza de piernas",
    exercises: list[PlannedExerciseIn] | None = None,
) -> uuid.UUID:
    if exercises is None:
        exercises = [
            PlannedExerciseIn(
                _exercise_id(engine, "back_squat"),
                sets=3,
                target_reps=8,
                target_weight_kg=Decimal(60),
                target_rir=2,
            ),
            PlannedExerciseIn(_exercise_id(engine, "plank"), sets=2, target_seconds=45),
        ]
    with Session(engine) as session:
        workout = strength.create_strength_workout(
            session,
            user_id,
            scheduled_on=scheduled_on,
            title=title,
            exercises=exercises,
            coach_reason="Base de fuerza.",
        )
        session.commit()
        return workout.id


def _planned_ids(client: TestClient, headers: Headers, workout_id: uuid.UUID) -> list[str]:
    body = client.get(f"/v1/strength/workouts/{workout_id}", headers=headers).json()
    return [item["id"] for item in body["exercises"]]


def _put_sets(
    client: TestClient, headers: Headers, workout_id: uuid.UUID, sets: list[dict[str, Any]]
) -> Any:
    return client.put(
        f"/v1/strength/workouts/{workout_id}/sets", headers=headers, json={"sets": sets}
    )


def _complete(client: TestClient, headers: Headers, workout_id: uuid.UUID, **values: Any) -> Any:
    body = {"started_at": STARTED_AT, "duration_s": 3000, "rpe": 7, **values}
    return client.post(f"/v1/strength/workouts/{workout_id}/complete", headers=headers, json=body)


# --- Catálogo --------------------------------------------------------------------------------


def test_catalog_is_loaded_by_the_migration(engine: Engine) -> None:
    with Session(engine) as session:
        rows = session.scalars(select(Exercise)).all()

    system = [row for row in rows if row.origin == ExerciseOrigin.SYSTEM]
    assert len(system) >= 45
    assert all(row.user_id is None for row in system)


@pytest.mark.parametrize(
    ("query", "slug"),
    [
        ("sentadilla bulgara", "bulgarian_split_squat"),
        ("SENTADILLA BÚLGARA", "bulgarian_split_squat"),
        ("rdl", "romanian_deadlift"),
        ("step up", "step_up"),
        ("subida al cajon", "step_up"),
        ("nórdico", "nordic_curl"),
    ],
)
def test_search_by_name_or_alias(
    db_client: TestClient, headers: Headers, query: str, slug: str
) -> None:
    response = db_client.get("/v1/strength/exercises", headers=headers, params={"q": query})

    assert response.status_code == 200
    assert slug in [item["slug"] for item in response.json()]


def test_search_ranks_prefix_matches_first(db_client: TestClient, headers: Headers) -> None:
    response = db_client.get("/v1/strength/exercises", headers=headers, params={"q": "peso muerto"})

    slugs = [item["slug"] for item in response.json()]
    assert slugs[0] == "deadlift"
    assert {"romanian_deadlift", "single_leg_romanian_deadlift"} <= set(slugs)


def test_search_without_query_lists_and_limits(db_client: TestClient, headers: Headers) -> None:
    response = db_client.get("/v1/strength/exercises", headers=headers, params={"limit": 5})

    assert response.status_code == 200
    assert len(response.json()) == 5


def test_search_includes_own_exercises_but_not_others(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    other = uuid.uuid4()
    with Session(engine) as session:
        session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": other})
        strength.create_exercise(
            session,
            athlete_id,
            slug="sled_push",
            name="Empuje de trineo",
            muscle_group=MuscleGroup.FULL_BODY,
            mode=ExerciseMode.SECONDS,
        )
        strength.create_exercise(
            session,
            other,
            slug="sled_pull",
            name="Arrastre de trineo",
            muscle_group=MuscleGroup.FULL_BODY,
            mode=ExerciseMode.SECONDS,
        )
        session.commit()
    try:
        response = db_client.get("/v1/strength/exercises", headers=headers, params={"q": "trineo"})
        assert [(item["slug"], item["origin"]) for item in response.json()] == [
            ("sled_push", "coach")
        ]
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": other})


# --- Entrenos planificados -------------------------------------------------------------------


def test_list_planned_workouts_by_range(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    inside = _workout(engine, athlete_id, scheduled_on=date(2026, 11, 20), title="B")
    first = _workout(engine, athlete_id, scheduled_on=date(2026, 11, 18), title="A")
    _workout(engine, athlete_id, scheduled_on=date(2026, 12, 1), title="Fuera")

    response = db_client.get(
        "/v1/planned-workouts", headers=headers, params={"from": "2026-11-18", "to": "2026-11-20"}
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [str(first), str(inside)]
    assert body[0]["sport"] == "strength"
    assert body[0]["status"] == "planned"
    assert body[0]["coach_reason"] == "Base de fuerza."
    assert body[0]["activity_id"] is None


def test_workout_detail(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    workout_id = _workout(engine, athlete_id)

    response = db_client.get(f"/v1/strength/workouts/{workout_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Fuerza de piernas"
    assert body["set_logs"] == []
    assert body["activity"] is None
    squat, plank = body["exercises"]
    assert squat["position"] == 1
    assert squat["exercise"]["slug"] == "back_squat"
    assert (squat["sets"], squat["target_reps"], squat["target_seconds"]) == (3, 8, None)
    assert (squat["target_weight_kg"], squat["target_rir"], squat["target_rpe"]) == (60.0, 2, None)
    assert plank["exercise"]["mode"] == "seconds"
    assert (plank["target_reps"], plank["target_seconds"]) == (None, 45)


def test_workout_of_another_athlete_is_not_found(
    engine: Engine, db_client: TestClient, make_token: TokenFactory, athlete_id: uuid.UUID
) -> None:
    workout_id = _workout(engine, athlete_id)
    other = {"Authorization": f"Bearer {make_token(sub=str(uuid.uuid4()))}"}

    assert db_client.get(f"/v1/strength/workouts/{workout_id}", headers=other).status_code == 404
    assert _put_sets(db_client, other, workout_id, []).status_code == 404
    assert _complete(db_client, other, workout_id).status_code == 404


def test_non_strength_workout_is_rejected(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    with Session(engine) as session:
        workout = PlannedWorkout(
            user_id=athlete_id, sport=Sport.CYCLING, scheduled_on=DAY, title="Rodaje"
        )
        session.add(workout)
        session.commit()
        workout_id = workout.id

    response = db_client.get(f"/v1/strength/workouts/{workout_id}", headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "not_strength"


def test_planned_target_must_match_exercise_mode(engine: Engine, athlete_id: uuid.UUID) -> None:
    from app.core.errors import UnprocessableError

    with pytest.raises(UnprocessableError) as exc:
        _workout(
            engine,
            athlete_id,
            exercises=[PlannedExerciseIn(_exercise_id(engine, "plank"), sets=3, target_reps=10)],
        )
    assert exc.value.code == "mode_mismatch"


# --- Registro de series ----------------------------------------------------------------------


def test_register_and_edit_sets(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    workout_id = _workout(engine, athlete_id)
    squat, plank = _planned_ids(db_client, headers, workout_id)
    lunge = str(_exercise_id(engine, "walking_lunge"))

    response = _put_sets(
        db_client,
        headers,
        workout_id,
        [
            {"planned_exercise_id": plank, "set_number": 1, "seconds": 45},
            {"planned_exercise_id": squat, "set_number": 2, "reps": 6, "weight_kg": 62.5},
            {"planned_exercise_id": squat, "set_number": 1, "reps": 8, "weight_kg": 60, "rir": 2},
            {"exercise_id": lunge, "set_number": 1, "reps": 10},
        ],
    )

    assert response.status_code == 200
    logs = response.json()["set_logs"]
    assert [(log["planned_exercise_id"], log["set_number"]) for log in logs] == [
        (squat, 1),
        (squat, 2),
        (plank, 1),
        (None, 1),
    ]
    assert logs[0]["weight_kg"] == 60.0
    assert logs[0]["rir"] == 2
    assert logs[1]["weight_kg"] == 62.5
    assert logs[2]["seconds"] == 45 and logs[2]["reps"] is None
    assert logs[3]["exercise_id"] == lunge
    assert all(log["activity_id"] is None and log["completed"] for log in logs)

    # Editar: la lista sustituye a la anterior.
    response = _put_sets(
        db_client,
        headers,
        workout_id,
        [{"planned_exercise_id": squat, "set_number": 1, "reps": 5, "completed": False}],
    )
    logs = response.json()["set_logs"]
    assert [(log["reps"], log["completed"]) for log in logs] == [(5, False)]


@pytest.mark.parametrize(
    ("sets", "code"),
    [
        (
            [{"planned_exercise_id": str(uuid.uuid4()), "set_number": 1, "reps": 5}],
            "unknown_planned_exercise",
        ),
        ([{"exercise_id": str(uuid.uuid4()), "set_number": 1, "reps": 5}], "unknown_exercise"),
        ([{"planned": 0, "set_number": 1, "seconds": 30}], "mode_mismatch"),
        ([{"planned": 1, "set_number": 1, "reps": 30}], "mode_mismatch"),
        (
            [
                {"planned": 0, "set_number": 1, "reps": 5},
                {"planned": 0, "set_number": 1, "reps": 6},
            ],
            "duplicate_set",
        ),
    ],
    ids=[
        "planificado_ajeno",
        "ejercicio_inexistente",
        "segundos_en_reps",
        "reps_en_segundos",
        "repetida",
    ],
)
def test_invalid_sets_are_rejected_without_changes(
    engine: Engine,
    db_client: TestClient,
    headers: Headers,
    athlete_id: uuid.UUID,
    sets: list[dict[str, Any]],
    code: str,
) -> None:
    workout_id = _workout(engine, athlete_id)
    planned = _planned_ids(db_client, headers, workout_id)
    _put_sets(
        db_client,
        headers,
        workout_id,
        [{"planned_exercise_id": planned[0], "set_number": 1, "reps": 8}],
    )
    for item in sets:
        if "planned" in item:
            item["planned_exercise_id"] = planned[item.pop("planned")]

    response = _put_sets(db_client, headers, workout_id, sets)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    with Session(engine) as session:
        count = (
            select(func.count())
            .select_from(StrengthSetLog)
            .where(StrengthSetLog.planned_workout_id == workout_id)
        )
        assert session.scalar(count) == 1


def test_other_athletes_exercise_cannot_be_logged(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    other = uuid.uuid4()
    with Session(engine) as session:
        session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": other})
        foreign = strength.create_exercise(
            session,
            other,
            slug="private",
            name="Privado",
            muscle_group=MuscleGroup.CORE,
            mode=ExerciseMode.REPS,
        ).id
        session.commit()
    try:
        workout_id = _workout(engine, athlete_id)
        response = _put_sets(
            db_client,
            headers,
            workout_id,
            [{"exercise_id": str(foreign), "set_number": 1, "reps": 5}],
        )
        assert response.json()["error"]["code"] == "unknown_exercise"
        assert (
            db_client.get(f"/v1/strength/exercises/{foreign}/last-log", headers=headers)
        ).status_code == 404
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": other})


def test_skipped_workout_cannot_be_logged_or_completed(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    workout_id = _workout(engine, athlete_id)
    with Session(engine) as session:
        session.get_one(PlannedWorkout, workout_id).status = PlannedWorkoutStatus.SKIPPED
        session.commit()

    assert _put_sets(db_client, headers, workout_id, []).status_code == 409
    assert _complete(db_client, headers, workout_id).status_code == 409


# --- Completar la sesión ---------------------------------------------------------------------


def test_complete_creates_strength_activity_with_session_rpe_load(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    workout_id = _workout(engine, athlete_id)
    squat, _ = _planned_ids(db_client, headers, workout_id)
    _put_sets(
        db_client,
        headers,
        workout_id,
        [{"planned_exercise_id": squat, "set_number": 1, "reps": 8, "weight_kg": 60}],
    )

    response = _complete(db_client, headers, workout_id, duration_s=3000, rpe=7)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    activity = body["activity"]
    assert body["activity_id"] == activity["id"]
    # session_rpe = 50 min × RPE 7.
    assert (activity["load"], activity["load_method"]) == (350.0, "session_rpe")
    assert (activity["elapsed_s"], activity["rpe"]) == (3000, 7)
    assert all(log["activity_id"] == activity["id"] for log in body["set_logs"])

    with Session(engine) as session:
        row = session.get_one(Activity, uuid.UUID(activity["id"]))
        assert (row.sport, row.source, row.title) == ("strength", "manual", "Fuerza de piernas")
        assert row.start_at == datetime(2026, 11, 19, 17, 30, tzinfo=UTC)
        assert row.load_method == LoadMethod.SESSION_RPE
        # La fuerza no suma en la carga diaria (CTL/ATL/TSB).
        day = session.get(DailyLoad, (athlete_id, DAY))
        assert day is not None and day.load == 0

    # Completar dos veces no crea otra actividad.
    again = _complete(db_client, headers, workout_id)
    assert again.status_code == 409
    with Session(engine) as session:
        count = select(func.count()).select_from(Activity).where(Activity.user_id == athlete_id)
        assert session.scalar(count) == 1


def test_sets_edited_after_completion_keep_the_activity(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    workout_id = _workout(engine, athlete_id)
    squat, _ = _planned_ids(db_client, headers, workout_id)
    activity_id = _complete(db_client, headers, workout_id).json()["activity_id"]

    response = _put_sets(
        db_client, headers, workout_id, [{"planned_exercise_id": squat, "set_number": 1, "reps": 8}]
    )

    assert response.status_code == 200
    assert [log["activity_id"] for log in response.json()["set_logs"]] == [activity_id]


# --- Último registro de un ejercicio ---------------------------------------------------------


def test_last_log_without_history(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    exercise_id = _exercise_id(engine, "back_squat")

    response = db_client.get(f"/v1/strength/exercises/{exercise_id}/last-log", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["exercise"]["slug"] == "back_squat"
    assert (body["performed_on"], body["activity_id"], body["sets"]) == (None, None, [])


def test_last_log_returns_latest_completed_session(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    exercise_id = _exercise_id(engine, "back_squat")

    def session_with(day: date, started_at: str, weights: list[float]) -> uuid.UUID:
        workout_id = _workout(engine, athlete_id, scheduled_on=day)
        squat, _ = _planned_ids(db_client, headers, workout_id)
        _put_sets(
            db_client,
            headers,
            workout_id,
            [
                {"planned_exercise_id": squat, "set_number": n, "reps": 8, "weight_kg": w}
                for n, w in enumerate(weights, start=1)
            ],
        )
        _complete(db_client, headers, workout_id, started_at=started_at)
        return workout_id

    session_with(date(2026, 11, 5), "2026-11-05T18:00:00+01:00", [50, 52.5])
    latest = session_with(date(2026, 11, 12), "2026-11-12T23:30:00+01:00", [55, 57.5, 60])
    session_with(date(2026, 11, 8), "2026-11-08T18:00:00+01:00", [40])
    # Una sesión en curso (sin completar) no cuenta.
    pending = _workout(engine, athlete_id, scheduled_on=date(2026, 11, 20))
    squat, _ = _planned_ids(db_client, headers, pending)
    _put_sets(
        db_client,
        headers,
        pending,
        [{"planned_exercise_id": squat, "set_number": 1, "reps": 8, "weight_kg": 80}],
    )

    response = db_client.get(f"/v1/strength/exercises/{exercise_id}/last-log", headers=headers)

    body = response.json()
    assert body["performed_on"] == "2026-11-12"
    assert body["planned_workout_id"] == str(latest)
    assert [(s["set_number"], s["reps"], s["weight_kg"]) for s in body["sets"]] == [
        (1, 8, 55.0),
        (2, 8, 57.5),
        (3, 8, 60.0),
    ]


def test_last_log_of_unknown_exercise(db_client: TestClient, headers: Headers) -> None:
    response = db_client.get(f"/v1/strength/exercises/{uuid.uuid4()}/last-log", headers=headers)

    assert response.status_code == 404


# --- Esquema ---------------------------------------------------------------------------------


def test_deleting_the_user_cascades_to_strength_data(
    engine: Engine, db_client: TestClient, headers: Headers, athlete_id: uuid.UUID
) -> None:
    with Session(engine) as session:
        strength.create_exercise(
            session,
            athlete_id,
            slug="own",
            name="Propio",
            muscle_group=MuscleGroup.CORE,
            mode=ExerciseMode.REPS,
        )
        session.commit()
    own = db_client.get("/v1/strength/exercises", headers=headers, params={"q": "propio"}).json()
    workout_id = _workout(
        engine,
        athlete_id,
        exercises=[PlannedExerciseIn(uuid.UUID(own[0]["id"]), sets=1, target_reps=5)],
    )
    (planned,) = _planned_ids(db_client, headers, workout_id)
    _put_sets(
        db_client,
        headers,
        workout_id,
        [{"planned_exercise_id": planned, "set_number": 1, "reps": 5}],
    )
    _complete(db_client, headers, workout_id)

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": athlete_id})
        remaining = conn.execute(
            text(
                "SELECT (SELECT count(*) FROM exercises WHERE user_id = :id)"
                " + (SELECT count(*) FROM planned_workouts WHERE user_id = :id)"
                " + (SELECT count(*) FROM planned_strength_exercises WHERE user_id = :id)"
                " + (SELECT count(*) FROM strength_set_logs WHERE user_id = :id)"
            ),
            {"id": athlete_id},
        ).scalar()
    assert remaining == 0


def test_used_exercise_cannot_be_deleted(engine: Engine, athlete_id: uuid.UUID) -> None:
    _workout(engine, athlete_id)

    with engine.connect() as conn, pytest.raises(IntegrityError):
        conn.execute(text("DELETE FROM exercises WHERE slug = 'back_squat'"))


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO exercises (slug, name, muscle_group, mode, origin, search_text) "
        "VALUES ('x', 'X', 'core', 'reps', 'coach', 'x')",
        "INSERT INTO exercises (slug, name, muscle_group, mode, origin, search_text) "
        "VALUES ('Back Squat', 'X', 'core', 'reps', 'system', 'x')",
        "INSERT INTO exercises (slug, name, muscle_group, mode, origin, search_text) "
        "VALUES ('back_squat', 'X', 'core', 'reps', 'system', 'x')",
        "INSERT INTO exercises (slug, name, muscle_group, mode, origin, search_text) "
        "VALUES ('y', 'Y', 'neck', 'reps', 'system', 'y')",
        "INSERT INTO planned_workouts (user_id, sport, scheduled_on, title, status) "
        "VALUES (:u, 'strength', '2026-11-19', 'x', 'later')",
        "INSERT INTO strength_set_logs (user_id, exercise_id, set_number, reps) "
        "SELECT :u, id, 1, 5 FROM exercises WHERE slug = 'plank'",
    ],
    ids=[
        "coach_sin_dueno",
        "slug_no_valido",
        "slug_repetido",
        "grupo_no_valido",
        "estado_no_valido",
        "serie_sin_sesion",
    ],
)
def test_check_constraints(session: Session, athlete_id: uuid.UUID, statement: str) -> None:
    with pytest.raises(IntegrityError):
        session.execute(text(statement), {"u": athlete_id})
