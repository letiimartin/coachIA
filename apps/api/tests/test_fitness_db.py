"""Carga de las actividades, recálculo histórico y serie de forma contra Postgres (#17)."""

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import TokenVerifier
from app.db.session import Database
from app.main import create_app
from app.metrics.fitness import fitness_series
from app.models import (
    Activity,
    ActivitySource,
    AthleteThreshold,
    DailyLoad,
    LoadMethod,
    Sport,
)
from app.services import fitness
from tests.conftest import (
    FakeJWKSClient,
    TokenFactory,
    database_url_for_tests,
    make_settings,
    requires_db,
)

pytestmark = requires_db

D0 = date(2026, 10, 1)
TODAY = date(2026, 10, 20)


def _at(day: date, hour: int = 8) -> datetime:
    # Europe/Madrid en octubre es UTC+2: 8:00 UTC sigue siendo el mismo día local.
    return datetime(day.year, day.month, day.day, hour, tzinfo=UTC)


def _ride(
    user_id: uuid.UUID, day: date, *, np_w: int = 200, moving_s: int = 3600, **extra: Any
) -> Activity:
    values: dict[str, Any] = {
        "user_id": user_id,
        "source": ActivitySource.WAHOO,
        "external_id": uuid.uuid4().hex[:16],
        "sport": Sport.CYCLING,
        "start_at": _at(day),
        "moving_s": moving_s,
        "elapsed_s": moving_s,
        "normalized_power_w": np_w,
        "avg_hr": 150,
        **extra,
    }
    return Activity(**values)


def _threshold(user_id: uuid.UUID, effective_from: date, **values: Any) -> AthleteThreshold:
    return AthleteThreshold(user_id=user_id, effective_from=effective_from, **values)


def _series(session: Session, user_id: uuid.UUID) -> list[tuple[date, Decimal, float, float]]:
    rows = session.scalars(
        select(DailyLoad)
        .where(DailyLoad.user_id == user_id)
        .order_by(DailyLoad.day)
        .execution_options(populate_existing=True)
    )
    return [(row.day, row.load, row.ctl, row.atl) for row in rows]


def _loads(session: Session, user_id: uuid.UUID) -> list[tuple[date, Decimal | None]]:
    rows = session.scalars(
        select(Activity)
        .where(Activity.user_id == user_id)
        .order_by(Activity.start_at)
        .execution_options(populate_existing=True)
    )
    return [(row.start_at.date(), row.load) for row in rows]


def _full_recompute(session: Session, user_id: uuid.UUID) -> list[Any]:
    session.execute(DailyLoad.__table__.delete().where(DailyLoad.user_id == user_id))
    fitness.recompute_from(session, user_id, date.min, today=TODAY)
    return _series(session, user_id)


# --- Cálculo de la carga y de la serie -------------------------------------------------------


def test_recompute_fills_activity_load_and_continuous_series(
    session: Session, athlete_id: uuid.UUID
) -> None:
    session.add(_threshold(athlete_id, D0, ftp_w=250, cycling_lthr_bpm=170))
    session.add_all([_ride(athlete_id, D0), _ride(athlete_id, D0 + timedelta(days=2), np_w=250)])
    session.flush()

    fitness.recompute_from(session, athlete_id, D0, today=TODAY)

    ride = session.scalars(select(Activity).order_by(Activity.start_at)).first()
    assert ride is not None
    # 1 h a NP 200 con FTP 250: IF 0.8 -> 64.
    assert (ride.load, ride.load_method, ride.intensity_factor) == (
        Decimal("64.0"),
        LoadMethod.POWER,
        Decimal("0.800"),
    )
    series = _series(session, athlete_id)
    assert [row[0] for row in series] == [D0 + timedelta(days=i) for i in range(20)]
    assert [row[1] for row in series[:4]] == [Decimal(v) for v in ("64.0", "0.0", "100.0", "0.0")]
    expected = fitness_series({D0: 64.0, D0 + timedelta(days=2): 100.0}, start=D0, end=TODAY)
    assert [float(row[2]) for row in series] == pytest.approx([d.ctl for d in expected], abs=1e-3)
    assert [float(row[3]) for row in series] == pytest.approx([d.atl for d in expected], abs=1e-3)
    # TSB de TrainingPeaks: CTL − ATL del día anterior.
    tsb = session.scalar(
        select(DailyLoad.tsb).where(
            DailyLoad.user_id == athlete_id, DailyLoad.day == D0 + timedelta(days=1)
        )
    )
    assert float(tsb or 0) == pytest.approx(expected[0].ctl - expected[0].atl, abs=1e-3)


def test_load_uses_threshold_in_force_on_activity_date_and_sport(
    session: Session, athlete_id: uuid.UUID
) -> None:
    session.add_all(
        [
            _threshold(
                athlete_id,
                D0,
                ftp_w=200,
                cycling_lthr_bpm=150,
                running_lthr_bpm=170,
                threshold_pace_s_per_km=250,
            ),
            _threshold(athlete_id, D0 + timedelta(days=5), ftp_w=250, running_lthr_bpm=170),
        ]
    )
    before = _ride(athlete_id, D0 + timedelta(days=4))
    after = _ride(athlete_id, D0 + timedelta(days=5))
    # Ciclismo sin potencia: FC sobre el LTHR de ciclismo.
    ride_hr = _ride(athlete_id, D0 + timedelta(days=4), np_w=0, avg_hr=150)
    # Carrera con potencia y FC: manda el ritmo (4 m/s = 250 s/km, el umbral).
    run = _ride(athlete_id, D0 + timedelta(days=3), sport=Sport.RUNNING, avg_speed_mps=4)
    # Carrera en cinta sin velocidad pero con pulso: FC sobre el LTHR de carrera.
    treadmill = _ride(athlete_id, D0 + timedelta(days=3), sport=Sport.RUNNING, avg_hr=170)
    # Trail con ritmo: sólo cuenta la FC sobre el LTHR de carrera.
    trail = _ride(
        athlete_id, D0 + timedelta(days=2), sport=Sport.TRAIL_RUNNING, avg_hr=170, avg_speed_mps=4
    )
    trail_no_hr = _ride(
        athlete_id, D0 + timedelta(days=1), sport=Sport.TRAIL_RUNNING, avg_hr=None, avg_speed_mps=4
    )
    # Sin moving_s no hay carga.
    no_moving = _ride(athlete_id, D0 + timedelta(days=7), moving_s=0)
    no_moving.moving_s = None
    session.add_all([before, after, ride_hr, run, treadmill, trail, trail_no_hr, no_moving])
    session.flush()

    fitness.recompute_from(session, athlete_id, D0, today=TODAY)

    assert (before.load, before.intensity_factor) == (Decimal("100.0"), Decimal("1.000"))
    assert (after.load, after.intensity_factor) == (Decimal("64.0"), Decimal("0.800"))
    assert (ride_hr.load, ride_hr.load_method) == (Decimal("100.0"), LoadMethod.HEART_RATE)
    assert (run.load, run.load_method, run.intensity_factor) == (
        Decimal("100.0"),
        LoadMethod.PACE,
        None,
    )
    assert (treadmill.load, treadmill.load_method) == (Decimal("100.0"), LoadMethod.HEART_RATE)
    assert (trail.load, trail.load_method) == (Decimal("100.0"), LoadMethod.HEART_RATE)
    assert (trail_no_hr.load, trail_no_hr.load_method) == (None, None)
    assert (no_moving.load, no_moving.load_method) == (None, None)


def test_duplicates_do_not_add_to_daily_load(session: Session, athlete_id: uuid.UUID) -> None:
    session.add(_threshold(athlete_id, D0, ftp_w=250))
    original = _ride(athlete_id, D0)
    session.add(original)
    session.flush()
    session.add(_ride(athlete_id, D0, source=ActivitySource.STRAVA, duplicate_of_id=original.id))
    session.flush()

    fitness.recompute_from(session, athlete_id, D0, today=TODAY)

    assert _series(session, athlete_id)[0][1] == Decimal("64.0")


def test_recompute_is_idempotent_and_partial_equals_full(
    session: Session, athlete_id: uuid.UUID
) -> None:
    session.add(_threshold(athlete_id, D0, ftp_w=250))
    session.add_all([_ride(athlete_id, D0 + timedelta(days=i), np_w=180 + i) for i in range(10)])
    session.flush()

    fitness.recompute_from(session, athlete_id, D0, today=TODAY)
    first = _series(session, athlete_id)
    fitness.recompute_from(session, athlete_id, D0, today=TODAY)
    assert _series(session, athlete_id) == first
    fitness.recompute_from(session, athlete_id, D0 + timedelta(days=6), today=TODAY)
    assert _series(session, athlete_id) == first
    assert _full_recompute(session, athlete_id) == first


def test_without_activities_the_series_is_empty(session: Session, athlete_id: uuid.UUID) -> None:
    fitness.recompute_from(session, athlete_id, D0, today=TODAY)
    assert _series(session, athlete_id) == []


def test_future_since_does_not_fail(session: Session, athlete_id: uuid.UUID) -> None:
    session.add(_ride(athlete_id, D0))
    session.flush()
    fitness.recompute_from(session, athlete_id, D0, today=TODAY)
    before = _series(session, athlete_id)

    fitness.recompute_from(session, athlete_id, TODAY + timedelta(days=10), today=TODAY)

    assert _series(session, athlete_id) == before


# --- Los tres casos del recálculo histórico ---------------------------------------------------


def test_backfill_of_older_activities_regenerates_the_series(
    session: Session, athlete_id: uuid.UUID
) -> None:
    session.add(_threshold(athlete_id, D0 - timedelta(days=30), ftp_w=250))
    session.add(_ride(athlete_id, D0 + timedelta(days=5)))
    session.flush()
    fitness.recompute_from(session, athlete_id, D0, today=TODAY)
    assert _series(session, athlete_id)[0][0] == D0 + timedelta(days=5)

    # Llega una actividad antigua (p. ej. un sync de histórico).
    old = _ride(athlete_id, D0 - timedelta(days=10), np_w=250)
    session.add(old)
    session.flush()
    fitness.recompute_since_activity(session, athlete_id, old.start_at, today=TODAY)

    assert old.load == Decimal("100.0")
    series = _series(session, athlete_id)
    assert series[0][:2] == (D0 - timedelta(days=10), Decimal("100.0"))
    assert series[-1][0] == TODAY
    # La CTL posterior arrastra la carga antigua.
    assert series == _full_recompute(session, athlete_id)


def test_modified_or_deleted_activity_regenerates_the_series(
    session: Session, athlete_id: uuid.UUID
) -> None:
    session.add(_threshold(athlete_id, D0, ftp_w=250))
    first = _ride(athlete_id, D0)
    changed = _ride(athlete_id, D0 + timedelta(days=3))
    session.add_all([first, changed])
    session.flush()
    fitness.recompute_from(session, athlete_id, D0, today=TODAY)

    changed.normalized_power_w = 250
    session.flush()
    # Protección de #22: el gancho automático no cambia una carga existente…
    fitness.recompute_since_activity(session, athlete_id, changed.start_at, today=TODAY)
    assert changed.load == Decimal("64.0")
    # …el recálculo explícito sí.
    fitness.recompute_from(
        session, athlete_id, changed.start_at.date(), today=TODAY, overwrite_existing=True
    )
    assert changed.load == Decimal("100.0")
    assert _series(session, athlete_id)[3][1] == Decimal("100.0")
    assert _series(session, athlete_id) == _full_recompute(session, athlete_id)

    start_at = changed.start_at
    session.delete(changed)
    session.flush()
    fitness.recompute_since_activity(session, athlete_id, start_at, today=TODAY)
    series = _series(session, athlete_id)
    assert series[3][1] == Decimal("0.0")
    assert series == _full_recompute(session, athlete_id)

    # Si se borra la primera, la serie empieza en la siguiente actividad (o desaparece).
    session.delete(first)
    session.flush()
    fitness.recompute_since_activity(session, athlete_id, first.start_at, today=TODAY)
    assert _series(session, athlete_id) == []


def test_threshold_change_recomputes_from_its_date(session: Session, athlete_id: uuid.UUID) -> None:
    session.add(_threshold(athlete_id, D0, ftp_w=250))
    early = _ride(athlete_id, D0 + timedelta(days=1))
    late = _ride(athlete_id, D0 + timedelta(days=8))
    session.add_all([early, late])
    session.flush()
    fitness.recompute_from(session, athlete_id, D0, today=TODAY)
    assert (early.load, late.load) == (Decimal("64.0"), Decimal("64.0"))

    session.add(_threshold(athlete_id, D0 + timedelta(days=5), ftp_w=200))
    session.flush()
    fitness.recompute_from(
        session, athlete_id, D0 + timedelta(days=5), today=TODAY, overwrite_existing=True
    )

    assert (early.load, late.load) == (Decimal("64.0"), Decimal("100.0"))
    assert _series(session, athlete_id)[7][1] == Decimal("100.0")  # Empieza en D0+1.
    assert _series(session, athlete_id) == _full_recompute(session, athlete_id)


# --- Protección de las cargas existentes y simulación (#22) -----------------------------------


def test_automatic_recompute_never_changes_or_clears_existing_loads(
    session: Session, athlete_id: uuid.UUID
) -> None:
    session.add(_threshold(athlete_id, D0, ftp_w=250))
    kept = _ride(athlete_id, D0, load=Decimal("80.0"), load_method=LoadMethod.HEART_RATE)
    # Con las reglas nuevas, un trail sin LTHR de carrera no tendría carga: se conserva.
    trail = _ride(
        athlete_id,
        D0 + timedelta(days=1),
        sport=Sport.TRAIL_RUNNING,
        load=Decimal("55.5"),
        load_method=LoadMethod.PACE,
    )
    rpe = _ride(
        athlete_id,
        D0 + timedelta(days=2),
        sport=Sport.TRAIL_RUNNING,
        avg_hr=None,
        load=Decimal("70.0"),
        load_method=LoadMethod.RPE,
    )
    new = _ride(athlete_id, D0 + timedelta(days=3))
    session.add_all([kept, trail, rpe, new])
    session.flush()

    fitness.recompute_from(session, athlete_id, D0, today=TODAY)

    assert (kept.load, kept.load_method) == (Decimal("80.0"), LoadMethod.HEART_RATE)
    assert (trail.load, trail.load_method) == (Decimal("55.5"), LoadMethod.PACE)
    assert (rpe.load, rpe.load_method) == (Decimal("70.0"), LoadMethod.RPE)
    # Las nuevas sí se calculan, y la serie usa las cargas conservadas.
    assert (new.load, new.load_method) == (Decimal("64.0"), LoadMethod.POWER)
    assert [row[1] for row in _series(session, athlete_id)[:4]] == [
        Decimal(v) for v in ("80.0", "55.5", "70.0", "64.0")
    ]

    # Un umbral nuevo (gancho automático) tampoco las toca.
    session.add(_threshold(athlete_id, D0 + timedelta(days=1), ftp_w=200, running_lthr_bpm=170))
    session.flush()
    fitness.recompute_from(session, athlete_id, D0 + timedelta(days=1), today=TODAY)
    assert (trail.load, new.load) == (Decimal("55.5"), Decimal("64.0"))


def test_simulation_reports_changes_without_writing(
    session: Session, athlete_id: uuid.UUID
) -> None:
    session.add(_threshold(athlete_id, D0, ftp_w=250, running_lthr_bpm=170))
    same = _ride(athlete_id, D0, load=Decimal("64.0"), load_method=LoadMethod.POWER)
    changed = _ride(athlete_id, D0 + timedelta(days=1), load=Decimal("90.0"))
    changed.load_method = LoadMethod.POWER
    method = _ride(
        athlete_id,
        D0 + timedelta(days=2),
        sport=Sport.TRAIL_RUNNING,
        avg_hr=170,
        load=Decimal("100.0"),
        load_method=LoadMethod.PACE,
    )
    cleared = _ride(
        athlete_id,
        D0 + timedelta(days=3),
        sport=Sport.RUNNING,
        avg_hr=None,
        load=Decimal("40.0"),
        load_method=LoadMethod.HEART_RATE,
    )
    rpe = _ride(
        athlete_id, D0 + timedelta(days=4), load=Decimal("10.0"), load_method=LoadMethod.RPE
    )
    session.add_all([same, changed, method, cleared, rpe])
    session.commit()

    changes = fitness.simulate_recompute(session, athlete_id)

    summary = [(c.activity_id, c.old_load, c.new_load, c.new_method, c.delta) for c in changes]
    assert summary == [
        (changed.id, Decimal("90.0"), Decimal("64.0"), LoadMethod.POWER, Decimal("-26.0")),
        (method.id, Decimal("100.0"), Decimal("100.0"), LoadMethod.HEART_RATE, Decimal("0.0")),
        (cleared.id, Decimal("40.0"), None, None, None),
    ]
    assert changes[1].old_method is LoadMethod.PACE
    # Desde una fecha, sólo las posteriores.
    later = fitness.simulate_recompute(session, athlete_id, D0 + timedelta(days=2))
    assert [c.activity_id for c in later] == [method.id, cleared.id]
    # Nada se ha escrito.
    assert not session.dirty and not session.new
    session.rollback()
    assert _loads(session, athlete_id) == [
        (D0 + timedelta(days=i), Decimal(v))
        for i, v in enumerate(("64.0", "90.0", "100.0", "40.0", "10.0"))
    ]
    assert _series(session, athlete_id) == []

    # Lo que la simulación anuncia es lo que hace el recálculo explícito.
    fitness.recompute_from(session, athlete_id, date.min, today=TODAY, overwrite_existing=True)
    assert fitness.simulate_recompute(session, athlete_id) == []
    assert (changed.load, method.load_method, cleared.load, rpe.load) == (
        Decimal("64.0"),
        LoadMethod.HEART_RATE,
        None,
        Decimal("10.0"),
    )


# --- Fuerza: session RPE, fuera de la carga diaria ---------------------------------------------


def _gym(user_id: uuid.UUID, day: date, **extra: Any) -> Activity:
    values: dict[str, Any] = {
        "sport": Sport.STRENGTH,
        "np_w": 0,
        "avg_hr": 130,
        **extra,
    }
    return _ride(user_id, day, **values)


def test_strength_load_is_session_rpe_and_never_counts_in_daily_load(
    session: Session, athlete_id: uuid.UUID
) -> None:
    session.add(_threshold(athlete_id, D0, ftp_w=250, running_lthr_bpm=170, cycling_lthr_bpm=165))
    ride = _ride(athlete_id, D0)
    with_rpe = _gym(athlete_id, D0, rpe=7)
    # Con FC pero sin RPE: sin carga (la FC nunca cuenta en fuerza).
    without_rpe = _gym(athlete_id, D0 + timedelta(days=1))
    # Sin tiempo en movimiento: el total.
    elapsed_only = _gym(athlete_id, D0 + timedelta(days=2), moving_s=0, elapsed_s=1800, rpe=5)
    elapsed_only.moving_s = None
    session.add_all([ride, with_rpe, without_rpe, elapsed_only])
    session.flush()

    fitness.recompute_from(session, athlete_id, D0, today=TODAY)

    assert (with_rpe.load, with_rpe.load_method, with_rpe.intensity_factor) == (
        Decimal("420.0"),
        LoadMethod.SESSION_RPE,
        None,
    )
    assert (without_rpe.load, without_rpe.load_method) == (None, None)
    assert (elapsed_only.load, elapsed_only.load_method) == (
        Decimal("150.0"),
        LoadMethod.SESSION_RPE,
    )
    # CTL/ATL sólo con la bici.
    series = _series(session, athlete_id)
    assert [row[1] for row in series[:3]] == [Decimal(v) for v in ("64.0", "0.0", "0.0")]
    expected = fitness_series({D0: 64.0}, start=D0, end=TODAY)
    assert [float(row[2]) for row in series] == pytest.approx([d.ctl for d in expected], abs=1e-3)


def test_old_strength_tss_counts_until_explicit_recompute(
    session: Session, athlete_id: uuid.UUID
) -> None:
    session.add(_threshold(athlete_id, D0, running_lthr_bpm=170))
    old = _gym(athlete_id, D0, load=Decimal("50.0"), load_method=LoadMethod.HEART_RATE, rpe=6)
    old_no_rpe = _gym(
        athlete_id, D0 + timedelta(days=1), load=Decimal("40.0"), load_method=LoadMethod.HEART_RATE
    )
    # Sesión nueva de fuerza: carga por session RPE, que nunca suma.
    new_gym = _gym(athlete_id, D0 + timedelta(days=2), rpe=8)
    session.add_all([old, old_no_rpe, new_gym])
    session.commit()

    # Protección: el gancho automático no la borra ni la cambia, y su TSS histórico sigue
    # contando en la curva hasta el recálculo explícito. La sesión nueva no suma.
    fitness.recompute_from(session, athlete_id, D0, today=TODAY)
    assert (old.load, old.load_method) == (Decimal("50.0"), LoadMethod.HEART_RATE)
    assert (new_gym.load, new_gym.load_method) == (Decimal("480.0"), LoadMethod.SESSION_RPE)
    assert [row[1] for row in _series(session, athlete_id)[:3]] == [
        Decimal(v) for v in ("50.0", "40.0", "0.0")
    ]
    protected_curve = _series(session, athlete_id)
    session.commit()

    # La simulación enseña cuánto cambia la curva al excluir ese TSS, sin escribir nada.
    simulation = fitness.simulate_curve(session, athlete_id, today=TODAY)
    assert not session.dirty and not session.new
    assert [(e.sport, e.activities, e.load) for e in simulation.excluded] == [
        (Sport.STRENGTH, 2, 90.0)
    ]
    with_it = fitness_series({D0: 50.0, D0 + timedelta(days=1): 40.0}, start=D0, end=TODAY)
    assert [d.ctl for d in simulation.current] == pytest.approx([d.ctl for d in with_it])
    assert [float(row[2]) for row in protected_curve] == pytest.approx(
        [d.ctl for d in simulation.current], abs=1e-3
    )
    assert {d.ctl for d in simulation.without_historical} == {0.0}
    assert simulation.exclusion_deltas[-1].ctl == pytest.approx(-with_it[-1].ctl)
    assert {d.ctl for d in simulation.after_recompute} == {0.0}

    changes = fitness.simulate_recompute(session, athlete_id)
    assert [(c.activity_id, c.old_method, c.new_load, c.new_method) for c in changes] == [
        (old.id, LoadMethod.HEART_RATE, Decimal("360.0"), LoadMethod.SESSION_RPE),
        (old_no_rpe.id, LoadMethod.HEART_RATE, None, None),
    ]

    # Recálculo explícito: el TSS se sustituye por session RPE (o se vacía) y deja de sumar.
    fitness.recompute_from(session, athlete_id, date.min, today=TODAY, overwrite_existing=True)
    assert (old.load, old.load_method) == (Decimal("360.0"), LoadMethod.SESSION_RPE)
    assert (old_no_rpe.load, old_no_rpe.load_method) == (None, None)
    assert {row[1] for row in _series(session, athlete_id)} == {Decimal("0.0")}


def test_activity_rpe_check(session: Session, athlete_id: uuid.UUID) -> None:
    for bad in (0, 11):
        with pytest.raises(IntegrityError), session.begin_nested():
            session.add(_gym(athlete_id, D0, rpe=bad))
            session.flush()


# --- Senderismo, natación y otros: sólo se registran (#22) ------------------------------------


def test_registered_only_sports_get_no_load_and_keep_their_history(
    session: Session, athlete_id: uuid.UUID
) -> None:
    session.add(_threshold(athlete_id, D0, ftp_w=250, cycling_lthr_bpm=150, running_lthr_bpm=150))
    ride = _ride(athlete_id, D0)
    # Históricas: carga por FC calculada con el LTHR único de antes.
    old_hike = _ride(
        athlete_id,
        D0 + timedelta(days=1),
        sport=Sport.HIKING,
        np_w=0,
        load=Decimal("90.0"),
        load_method=LoadMethod.HEART_RATE,
    )
    old_swim = _ride(
        athlete_id,
        D0 + timedelta(days=2),
        sport=Sport.SWIMMING,
        np_w=0,
        load=Decimal("40.0"),
        load_method=LoadMethod.HEART_RATE,
    )
    # Nueva, con FC y LTHR de carrera: no se le calcula carga.
    new_hike = _ride(athlete_id, D0 + timedelta(days=3), sport=Sport.HIKING, np_w=0, avg_hr=150)
    session.add_all([ride, old_hike, old_swim, new_hike])
    session.commit()

    # Automático (con protección): la curva no cambia; las históricas siguen sumando.
    fitness.recompute_from(session, athlete_id, D0, today=TODAY)
    assert (new_hike.load, new_hike.load_method) == (None, None)
    assert [row[1] for row in _series(session, athlete_id)[:4]] == [
        Decimal(v) for v in ("64.0", "90.0", "40.0", "0.0")
    ]
    protected_curve = _series(session, athlete_id)
    session.commit()

    # La simulación enseña cuánto cambia la curva al excluirlas, sin escribir nada.
    simulation = fitness.simulate_curve(session, athlete_id, today=TODAY)
    assert not session.dirty and not session.new
    assert [(e.sport, e.activities, e.load) for e in simulation.excluded] == [
        (Sport.HIKING, 1, 90.0),
        (Sport.SWIMMING, 1, 40.0),
    ]
    with_them = fitness_series(
        {D0: 64.0, D0 + timedelta(days=1): 90.0, D0 + timedelta(days=2): 40.0}, start=D0, end=TODAY
    )
    without_them = fitness_series({D0: 64.0}, start=D0, end=TODAY)
    assert [d.ctl for d in simulation.current] == pytest.approx([d.ctl for d in with_them])
    assert [d.ctl for d in simulation.without_historical] == pytest.approx(
        [d.ctl for d in without_them]
    )
    assert simulation.exclusion_deltas[-1].ctl == pytest.approx(
        without_them[-1].ctl - with_them[-1].ctl
    )
    assert simulation.exclusion_deltas[0].ctl == 0
    assert [d.ctl for d in simulation.after_recompute] == pytest.approx(
        [d.ctl for d in without_them]
    )
    # La curva simulada «actual» es la guardada.
    assert [float(row[2]) for row in protected_curve] == pytest.approx(
        [d.ctl for d in simulation.current], abs=1e-3
    )
    assert _series(session, athlete_id) == protected_curve

    # Recálculo explícito: las excluye de la curva, pero conserva su carga histórica.
    fitness.recompute_from(session, athlete_id, date.min, today=TODAY, overwrite_existing=True)
    assert (old_hike.load, old_hike.load_method) == (Decimal("90.0"), LoadMethod.HEART_RATE)
    assert (old_swim.load, old_swim.load_method) == (Decimal("40.0"), LoadMethod.HEART_RATE)
    assert new_hike.load is None
    assert [row[1] for row in _series(session, athlete_id)[:4]] == [
        Decimal(v) for v in ("64.0", "0.0", "0.0", "0.0")
    ]
    assert fitness.simulate_recompute(session, athlete_id) == []


def test_simulate_curve_without_activities(session: Session, athlete_id: uuid.UUID) -> None:
    simulation = fitness.simulate_curve(session, athlete_id, today=TODAY)
    assert simulation.current == simulation.exclusion_deltas == simulation.excluded == []


# --- Lectura de la serie -----------------------------------------------------------------------


def test_fitness_range_pads_before_and_rests_after(session: Session, athlete_id: uuid.UUID) -> None:
    session.add(_threshold(athlete_id, D0, ftp_w=250))
    session.add(_ride(athlete_id, D0, np_w=250))
    session.flush()
    fitness.recompute_from(session, athlete_id, D0, today=D0 + timedelta(days=1))

    days = fitness.fitness_range(
        session, athlete_id, D0 - timedelta(days=2), D0 + timedelta(days=4)
    )

    assert [d.day for d in days] == [D0 + timedelta(days=i) for i in range(-2, 5)]
    assert [(d.load, d.ctl, d.atl, d.tsb) for d in days[:2]] == [(0.0, 0.0, 0.0, 0.0)] * 2
    expected = fitness_series({D0: 100.0}, start=D0, end=D0 + timedelta(days=4))
    assert [d.ctl for d in days[2:]] == pytest.approx([d.ctl for d in expected], abs=1e-3)
    assert [d.tsb for d in days[2:]] == pytest.approx([d.tsb for d in expected], abs=1e-3)

    # Un rango entero posterior a la última fila sigue decayendo desde el último estado.
    later = fitness.fitness_range(
        session, athlete_id, D0 + timedelta(days=3), D0 + timedelta(days=4)
    )
    assert [d.atl for d in later] == pytest.approx([d.atl for d in expected[3:]], abs=1e-3)


# --- Endpoints -----------------------------------------------------------------------------------


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
def headers(make_token: TokenFactory, user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(sub=str(user_id))}"}


def test_post_threshold_with_past_date_recomputes_load(
    db_client: TestClient, headers: dict[str, str], engine: Engine, athlete_id: uuid.UUID
) -> None:
    day = date.today() - timedelta(days=3)
    with Session(engine) as session:
        session.add(_ride(athlete_id, day))
        session.commit()

    response = db_client.post(
        "/v1/athlete/thresholds",
        headers=headers,
        json={"effective_from": (day - timedelta(days=1)).isoformat(), "ftp_w": 250},
    )
    assert response.status_code == 201

    with Session(engine) as session:
        assert _loads(session, athlete_id) == [(day, Decimal("64.0"))]

    series = db_client.get(
        "/v1/athlete/fitness",
        headers=headers,
        params={"from": day.isoformat(), "to": (day + timedelta(days=1)).isoformat()},
    )
    assert series.status_code == 200
    body = series.json()
    assert body["from"] == day.isoformat()
    assert [d["load"] for d in body["days"]] == [64.0, 0.0]
    assert body["days"][0]["ctl"] == round(64 / 42, 1)
    assert body["days"][0]["tsb"] == 0.0
    assert body["days"][1]["tsb"] == round(64 / 42 - 64 / 7, 1)


def test_fitness_endpoint_without_data_returns_zeros(
    db_client: TestClient, headers: dict[str, str], user_id: uuid.UUID
) -> None:
    response = db_client.get(
        "/v1/athlete/fitness", headers=headers, params={"from": "2026-01-01", "to": "2026-01-03"}
    )
    assert response.status_code == 200
    assert [d["ctl"] for d in response.json()["days"]] == [0.0, 0.0, 0.0]


@pytest.mark.parametrize(
    "params",
    [
        {"from": "2026-01-03", "to": "2026-01-01"},
        {"from": "2025-01-01", "to": "2026-01-02"},
        {"from": "2026-01-01"},
    ],
)
def test_fitness_endpoint_validates_range(
    db_client: TestClient, headers: dict[str, str], params: dict[str, str]
) -> None:
    response = db_client.get("/v1/athlete/fitness", headers=headers, params=params)
    assert response.status_code == 422


def test_fitness_endpoint_requires_auth(db_client: TestClient) -> None:
    response = db_client.get(
        "/v1/athlete/fitness", params={"from": "2026-01-01", "to": "2026-01-03"}
    )
    assert response.status_code == 401
