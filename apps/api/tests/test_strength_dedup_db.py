"""Sesiones de fuerza de Wahoo y deduplicación con la registrada en la app (#32), con Postgres.

Wahoo está simulado: no se activa ninguna sincronización real.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from app.core.crypto import TokenCipher
from app.integrations.wahoo import service, sync
from app.integrations.wahoo.client import WahooClient, WahooTokens
from app.models import Activity, ActivitySource, DailyLoad, Exercise, LoadMethod, StrengthSetLog
from app.schemas.strength import StrengthSetIn
from app.services import strength
from app.services.strength import PlannedExerciseIn
from app.services.strength_dedup import APP_RECORDED_KEY
from tests.conftest import FERNET_KEY, make_settings, requires_db

pytestmark = requires_db

DAY = date(2026, 11, 19)
# 18:30 en Madrid (zona por defecto del atleta).
STARTED_AT = datetime(2026, 11, 19, 17, 30, tzinfo=UTC)


class FakeWahoo:
    """Wahoo simulado: una única página con los workouts de `self.workouts`."""

    def __init__(self) -> None:
        self.workouts: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/workouts":
            body = {"workouts": self.workouts, "total": len(self.workouts), "per_page": 50}
            return httpx.Response(200, json=body)
        return httpx.Response(404)


def _workout(
    workout_id: int,
    starts: str = "2026-11-19T17:35:00.000Z",
    *,
    type_id: int = 42,
    total_s: str | None = "3300.00",
    hr: str | None = "118.00",
) -> dict[str, Any]:
    return {
        "id": workout_id,
        "starts": starts,
        "name": "Fuerza",
        "workout_type_id": type_id,
        "workout_summary": {
            "duration_total_accum": total_s,
            "duration_active_accum": "2400.00",
            "heart_rate_avg": hr,
            "calories_accum": "320.00",
            "time_zone": "Europe/Madrid",
        },
    }


@pytest.fixture
def fake_wahoo() -> FakeWahoo:
    return FakeWahoo()


@pytest.fixture
def run_sync(
    engine: Engine, athlete_id: uuid.UUID, fake_wahoo: FakeWahoo
) -> Callable[[], sync.SyncResult]:
    cipher = TokenCipher(FERNET_KEY)
    client = WahooClient(make_settings(), httpx.Client(transport=httpx.MockTransport(fake_wahoo)))
    with Session(engine) as session:
        tokens = WahooTokens("access-1", "refresh-1", 3600, ["workouts_read"])
        service.save_tokens(session, cipher, athlete_id, tokens)

    def _run() -> sync.SyncResult:
        with Session(engine) as session:
            # Sin cursor: cada sync vuelve a leer todos los workouts de la página.
            integration = service.get_integration(session, athlete_id)
            assert integration is not None
            integration.sync_cursor = {}
            session.commit()
            return sync.sync_user(session, cipher, client, athlete_id)

    return _run


def _exercise_id(session: Session, slug: str) -> uuid.UUID:
    return session.scalars(
        select(Exercise.id).where(Exercise.slug == slug, Exercise.user_id.is_(None))
    ).one()


def _complete_app_session(
    engine: Engine,
    user_id: uuid.UUID,
    *,
    started_at: datetime = STARTED_AT,
    duration_s: int = 3000,
    rpe: int = 7,
) -> uuid.UUID:
    """Sesión planificada con una serie registrada y completada en la app. Devuelve la actividad."""
    with Session(engine) as session:
        squat = _exercise_id(session, "back_squat")
        workout = strength.create_strength_workout(
            session,
            user_id,
            scheduled_on=started_at.date(),
            title="Fuerza de piernas",
            exercises=[PlannedExerciseIn(squat, sets=1, target_reps=8)],
        )
        session.commit()
        planned, _ = strength.get_strength_workout(session, user_id, workout.id).exercises[0]
        strength.replace_sets(
            session,
            user_id,
            workout.id,
            [
                StrengthSetIn(
                    planned_exercise_id=planned.id,
                    set_number=1,
                    reps=8,
                    weight_kg=Decimal(60),
                    rpe=8,
                )
            ],
        )
        detail = strength.complete_workout(
            session, user_id, workout.id, started_at=started_at, duration_s=duration_s, rpe=rpe
        )
        assert detail.workout.activity_id is not None
        return detail.workout.activity_id


def _activities(engine: Engine, user_id: uuid.UUID) -> list[Activity]:
    with Session(engine) as session:
        return list(
            session.scalars(
                select(Activity)
                .where(Activity.user_id == user_id)
                .order_by(Activity.source, Activity.start_at)
            )
        )


def _sets_by_activity(engine: Engine, user_id: uuid.UUID) -> dict[uuid.UUID | None, int]:
    with Session(engine) as session:
        rows = session.execute(
            select(StrengthSetLog.activity_id, func.count())
            .where(StrengthSetLog.user_id == user_id)
            .group_by(StrengthSetLog.activity_id)
        ).all()
    return {activity_id: count for activity_id, count in rows}


def test_wahoo_strength_without_app_session_keeps_only_what_arrives(
    engine: Engine, athlete_id: uuid.UUID, fake_wahoo: FakeWahoo, run_sync: Any
) -> None:
    fake_wahoo.workouts = [_workout(900)]

    run_sync()

    (activity,) = _activities(engine, athlete_id)
    assert (activity.source, activity.sport, activity.sub_sport) == ("wahoo", "strength", "workout")
    assert (activity.elapsed_s, activity.avg_hr, activity.calories) == (3300, 118, 320)
    # Sin RPE no hay carga session_rpe; nunca se crean ejercicios ni series.
    assert (activity.rpe, activity.load, activity.load_method) == (None, None, None)
    assert activity.duplicate_of_id is None
    assert _sets_by_activity(engine, athlete_id) == {}


def test_wahoo_synced_after_the_app_session_is_linked(
    engine: Engine, athlete_id: uuid.UUID, fake_wahoo: FakeWahoo, run_sync: Any
) -> None:
    app_id = _complete_app_session(engine, athlete_id, duration_s=3000, rpe=7)
    fake_wahoo.workouts = [_workout(900, total_s="3300.00", hr="118.00")]

    run_sync()

    app, wahoo = _activities(engine, athlete_id)
    assert (app.id, app.source, wahoo.source) == (app_id, "manual", "wahoo")
    assert wahoo.duplicate_of_id == app.id
    assert app.duplicate_of_id is None
    # De Wahoo: duración y FC. De la app: RPE y series. La carga se rehace: 55 min × RPE 7.
    assert (app.elapsed_s, app.moving_s, app.avg_hr, app.rpe) == (3300, 3300, 118, 7)
    assert (app.load, app.load_method) == (Decimal("385.0"), LoadMethod.SESSION_RPE)
    assert app.raw[APP_RECORDED_KEY]["elapsed_s"] == 3000
    assert (wahoo.load, wahoo.calories) == (None, 320)
    assert _sets_by_activity(engine, athlete_id) == {app.id: 1}
    with Session(engine) as session:
        day = session.get(DailyLoad, (athlete_id, DAY))
        assert day is not None and day.load == 0  # La fuerza no suma en CTL/ATL/TSB.

    # Repetir el sync no cambia nada.
    assert run_sync().unchanged == 1
    assert [(a.id, a.duplicate_of_id, a.load) for a in _activities(engine, athlete_id)] == [
        (app.id, None, Decimal("385.0")),
        (wahoo.id, app.id, None),
    ]


def test_app_session_completed_after_the_wahoo_sync_is_linked(
    engine: Engine, athlete_id: uuid.UUID, fake_wahoo: FakeWahoo, run_sync: Any
) -> None:
    fake_wahoo.workouts = [_workout(900, total_s="2700.00", hr="121.00")]
    run_sync()

    app_id = _complete_app_session(engine, athlete_id, duration_s=3000, rpe=6)

    app, wahoo = _activities(engine, athlete_id)
    assert app.id == app_id
    assert wahoo.duplicate_of_id == app.id
    # 45 min × RPE 6.
    assert (app.elapsed_s, app.avg_hr) == (2700, 121)
    assert (app.load, app.load_method) == (Decimal("270.0"), LoadMethod.SESSION_RPE)


def test_wahoo_edit_of_a_linked_session_is_copied_again(
    engine: Engine, athlete_id: uuid.UUID, fake_wahoo: FakeWahoo, run_sync: Any
) -> None:
    _complete_app_session(engine, athlete_id, duration_s=3000, rpe=7)
    fake_wahoo.workouts = [_workout(900, total_s="3300.00")]
    run_sync()

    fake_wahoo.workouts = [_workout(900, total_s="3120.00", hr="125.00")]
    assert run_sync().updated == 1

    app, wahoo = _activities(engine, athlete_id)
    assert wahoo.duplicate_of_id == app.id
    # 52 min × RPE 7; lo registrado en la app se conserva.
    assert (app.elapsed_s, app.avg_hr, app.load) == (3120, 125, Decimal("364.0"))
    assert app.raw[APP_RECORDED_KEY]["elapsed_s"] == 3000


@pytest.mark.parametrize(
    "workouts",
    [
        # Inicio 45 minutos después.
        [_workout(900, "2026-11-19T18:15:00.000Z")],
        # Duración un 30 % mayor.
        [_workout(900, total_s="3900.00")],
        # Sin duración: no se puede comparar.
        [{**_workout(900), "workout_summary": {"heart_rate_avg": "118.00"}}],
        # Otro deporte el mismo rato.
        [_workout(900, type_id=66)],
        # Dos candidatas de Wahoo: no hay una coincidencia clara.
        [_workout(900), _workout(901, "2026-11-19T17:40:00.000Z")],
    ],
)
def test_without_a_single_clear_match_activities_stay_separate(
    engine: Engine,
    athlete_id: uuid.UUID,
    fake_wahoo: FakeWahoo,
    run_sync: Any,
    workouts: list[dict[str, Any]],
) -> None:
    _complete_app_session(engine, athlete_id, duration_s=3000, rpe=7)
    fake_wahoo.workouts = workouts

    run_sync()

    activities = _activities(engine, athlete_id)
    assert len(activities) == 1 + len(workouts)
    assert all(a.duplicate_of_id is None for a in activities)
    app = next(a for a in activities if a.source == ActivitySource.MANUAL)
    assert (app.elapsed_s, app.avg_hr, app.load) == (3000, None, Decimal("350.0"))
    assert APP_RECORDED_KEY not in app.raw


def test_two_app_sessions_on_the_same_day_are_not_linked(
    engine: Engine, athlete_id: uuid.UUID, fake_wahoo: FakeWahoo, run_sync: Any
) -> None:
    _complete_app_session(engine, athlete_id)
    _complete_app_session(engine, athlete_id, started_at=datetime(2026, 11, 19, 17, 50, tzinfo=UTC))
    fake_wahoo.workouts = [_workout(900, "2026-11-19T17:40:00.000Z")]

    run_sync()

    assert all(a.duplicate_of_id is None for a in _activities(engine, athlete_id))


def test_other_athletes_sessions_are_never_linked(
    engine: Engine, athlete_id: uuid.UUID, fake_wahoo: FakeWahoo, run_sync: Any
) -> None:
    other = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": other})
        conn.execute(text("INSERT INTO athlete_profiles (user_id) VALUES (:id)"), {"id": other})
    try:
        _complete_app_session(engine, other)
        fake_wahoo.workouts = [_workout(900)]

        run_sync()

        (wahoo,) = _activities(engine, athlete_id)
        assert wahoo.duplicate_of_id is None
        (app,) = _activities(engine, other)
        assert app.elapsed_s == 3000
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": other})
