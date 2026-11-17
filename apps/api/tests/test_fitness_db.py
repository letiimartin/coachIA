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
    session.add(_threshold(athlete_id, D0, ftp_w=250, lthr_bpm=170))
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
            _threshold(athlete_id, D0, ftp_w=200, lthr_bpm=170),
            _threshold(athlete_id, D0 + timedelta(days=5), ftp_w=250, lthr_bpm=170),
        ]
    )
    before = _ride(athlete_id, D0 + timedelta(days=4))
    after = _ride(athlete_id, D0 + timedelta(days=5))
    # Carrera con potencia: el FTP es de bici, así que se usa la FC (sin IF publicado).
    run = _ride(athlete_id, D0 + timedelta(days=6), sport=Sport.RUNNING, avg_hr=170)
    # Sin moving_s no hay carga.
    no_moving = _ride(athlete_id, D0 + timedelta(days=7), moving_s=0)
    no_moving.moving_s = None
    session.add_all([before, after, run, no_moving])
    session.flush()

    fitness.recompute_from(session, athlete_id, D0, today=TODAY)

    assert (before.load, before.intensity_factor) == (Decimal("100.0"), Decimal("1.000"))
    assert (after.load, after.intensity_factor) == (Decimal("64.0"), Decimal("0.800"))
    assert (run.load, run.load_method, run.intensity_factor) == (
        Decimal("100.0"),
        LoadMethod.HEART_RATE,
        None,
    )
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
    fitness.recompute_since_activity(session, athlete_id, changed.start_at, today=TODAY)
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
    fitness.recompute_from(session, athlete_id, D0 + timedelta(days=5), today=TODAY)

    assert (early.load, late.load) == (Decimal("64.0"), Decimal("100.0"))
    assert _series(session, athlete_id)[7][1] == Decimal("100.0")  # Empieza en D0+1.
    assert _series(session, athlete_id) == _full_recompute(session, athlete_id)


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
