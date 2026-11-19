"""Criterio de deduplicación de sesiones de fuerza (#32), sin BD."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from app.integrations.wahoo.mapper import map_workout
from app.metrics.load import activity_load
from app.models import Activity, ActivitySource, LoadMethod, Sport
from app.services.strength_dedup import (
    APP_RECORDED_KEY,
    apply_device_metrics,
    is_match,
    match_pairs,
)

TZ = ZoneInfo("Europe/Madrid")
USER = uuid.uuid4()
# 18:30 en Madrid.
START = datetime(2026, 11, 19, 17, 30, tzinfo=UTC)


def _app(**values: Any) -> Activity:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "user_id": USER,
        "source": ActivitySource.MANUAL,
        "sport": Sport.STRENGTH,
        "start_at": START,
        "elapsed_s": 3000,
        "moving_s": 3000,
        "rpe": 7,
        "load": Decimal("350.0"),
        "load_method": LoadMethod.SESSION_RPE,
        "raw": {},
    }
    return Activity(**{**base, **values})


def _wahoo(**values: Any) -> Activity:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "user_id": USER,
        "source": ActivitySource.WAHOO,
        "external_id": "1",
        "sport": Sport.STRENGTH,
        "start_at": START + timedelta(minutes=5),
        "elapsed_s": 3300,
        "moving_s": 2400,
        "avg_hr": 118,
        "max_hr": None,
        "raw": {},
    }
    return Activity(**{**base, **values})


def test_same_session_matches() -> None:
    assert is_match(_app(), _wahoo(), TZ)


@pytest.mark.parametrize(
    ("app", "wahoo"),
    [
        # Inicio: hasta 30 minutos.
        ({}, {"start_at": START + timedelta(minutes=30)}),
        ({}, {"start_at": START - timedelta(minutes=30)}),
        # Duración: hasta un 20 % de la de la app (3000 s → 2400…3600 s).
        ({}, {"elapsed_s": 3600}),
        ({}, {"elapsed_s": 2400}),
        # Sin duración total, la activa.
        ({}, {"elapsed_s": None, "moving_s": 3100}),
    ],
)
def test_tolerances_are_inclusive(app: dict[str, Any], wahoo: dict[str, Any]) -> None:
    assert is_match(_app(**app), _wahoo(**wahoo), TZ)


@pytest.mark.parametrize(
    ("app", "wahoo"),
    [
        ({}, {"start_at": START + timedelta(minutes=31)}),
        ({}, {"elapsed_s": 3601}),
        ({}, {"elapsed_s": 2399}),
        # Faltan datos para comparar: quedan separadas.
        ({}, {"elapsed_s": None, "moving_s": None}),
        ({"elapsed_s": None, "moving_s": None}, {}),
        ({}, {"elapsed_s": 0, "moving_s": 0}),
        # Sólo fuerza, de la misma persona y con una de la app y otra del dispositivo.
        ({}, {"sport": Sport.OTHER}),
        ({"sport": Sport.CYCLING}, {}),
        ({}, {"user_id": uuid.uuid4()}),
        ({}, {"source": ActivitySource.MANUAL}),
        ({"source": ActivitySource.WAHOO}, {}),
        ({}, {"source": ActivitySource.STRAVA}),
    ],
)
def test_outside_criteria_does_not_match(app: dict[str, Any], wahoo: dict[str, Any]) -> None:
    assert not is_match(_app(**app), _wahoo(**wahoo), TZ)


def test_different_local_day_does_not_match_even_within_30_minutes() -> None:
    # 23:50 y 00:10 en Madrid: 20 minutos, pero distinto día local.
    late = datetime(2026, 11, 19, 22, 50, tzinfo=UTC)
    app = _app(start_at=late)
    assert not is_match(app, _wahoo(start_at=late + timedelta(minutes=20)), TZ)
    assert is_match(app, _wahoo(start_at=late + timedelta(minutes=5)), TZ)


def test_compares_with_the_duration_recorded_in_the_app() -> None:
    # Tras copiar la de Wahoo, la comparación sigue usando la registrada en la app.
    app = _app(elapsed_s=5000, moving_s=5000, raw={APP_RECORDED_KEY: {"elapsed_s": 3000}})
    assert is_match(app, _wahoo(elapsed_s=3000), TZ)
    assert not is_match(app, _wahoo(elapsed_s=5000), TZ)


def test_single_clear_match_is_paired() -> None:
    app, wahoo = _app(), _wahoo()
    assert match_pairs([app], [wahoo], TZ) == [(app, wahoo)]


def test_two_device_candidates_for_one_app_session_stay_separate() -> None:
    app = _app()
    first, second = _wahoo(), _wahoo(start_at=START + timedelta(minutes=10))
    assert match_pairs([app], [first, second], TZ) == []


def test_two_app_candidates_for_one_device_session_stay_separate() -> None:
    wahoo = _wahoo()
    other = _app(start_at=START + timedelta(minutes=20))
    assert match_pairs([_app(), other], [wahoo], TZ) == []


def test_unambiguous_pairs_are_kept_when_another_pair_is_ambiguous() -> None:
    morning = START - timedelta(hours=8)
    app_morning, wahoo_morning = _app(start_at=morning), _wahoo(start_at=morning)
    app, first, second = _app(), _wahoo(), _wahoo(start_at=START + timedelta(minutes=10))
    pairs = match_pairs([app_morning, app], [wahoo_morning, first, second], TZ)
    assert pairs == [(app_morning, wahoo_morning)]


def test_apply_takes_duration_and_hr_and_keeps_rpe_and_app_values() -> None:
    app, wahoo = _app(), _wahoo(elapsed_s=3300, avg_hr=118, max_hr=150)

    assert apply_device_metrics(app, wahoo)

    assert (app.elapsed_s, app.moving_s, app.avg_hr, app.max_hr) == (3300, 3300, 118, 150)
    assert app.rpe == 7
    # La carga session_rpe se vacía para que el recálculo la rehaga con la duración nueva.
    assert (app.load, app.load_method) == (None, None)
    assert app.raw[APP_RECORDED_KEY] == {
        "elapsed_s": 3000,
        "moving_s": 3000,
        "avg_hr": None,
        "max_hr": None,
    }
    # Repetirlo no cambia nada ni pisa lo registrado en la app.
    app.load, app.load_method = Decimal("385.0"), LoadMethod.SESSION_RPE
    assert not apply_device_metrics(app, wahoo)
    assert (app.load, app.load_method) == (Decimal("385.0"), LoadMethod.SESSION_RPE)
    assert app.raw[APP_RECORDED_KEY]["elapsed_s"] == 3000


@pytest.mark.parametrize("hr", [None, 0, 10, 300])
def test_invalid_device_values_are_not_copied(hr: int | None) -> None:
    app = _app(avg_hr=110)
    apply_device_metrics(app, _wahoo(elapsed_s=None, moving_s=None, avg_hr=hr, max_hr=hr))
    assert (app.elapsed_s, app.avg_hr, app.max_hr) == (3000, 110, None)
    assert (app.load, app.load_method) == (Decimal("350.0"), LoadMethod.SESSION_RPE)


def test_wahoo_strength_workout_keeps_only_what_arrives() -> None:
    workout = {"id": 900, "starts": "2026-11-19T17:35:00.000Z", "workout_type_id": 42}
    summary = {
        "duration_total_accum": "3300.00",
        "duration_active_accum": "2400.00",
        "heart_rate_avg": "118.00",
        "calories_accum": "320.00",
        "distance_accum": "0.00",
    }
    values = map_workout(workout, summary).values

    assert (values["sport"], values["sub_sport"]) == (Sport.STRENGTH, "workout")
    assert (values["elapsed_s"], values["avg_hr"], values["calories"]) == (3300, 118, 320)
    # Wahoo no da RPE: no hay carga session_rpe (ni ninguna otra para la fuerza).
    assert "rpe" not in values and "load" not in values
    assert activity_load(Sport.STRENGTH, 2400.0, elapsed_s=3300.0, avg_hr_bpm=118.0) is None
