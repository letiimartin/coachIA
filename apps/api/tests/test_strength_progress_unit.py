"""Rendimiento de fuerza (#33) sin BD: cifras de un ejercicio en una sesión y semanas."""

import uuid
from datetime import date
from decimal import Decimal

from app.models import StrengthSetLog
from app.services.strength_progress import summarize_session, week_start

ACTIVITY = uuid.uuid4()
DAY = date(2026, 11, 17)


def _log(
    reps: int | None = None, weight: str | None = None, seconds: int | None = None
) -> StrengthSetLog:
    return StrengthSetLog(
        reps=reps,
        seconds=seconds,
        weight_kg=None if weight is None else Decimal(weight),
        planned_workout_id=None,
    )


def test_week_starts_on_monday() -> None:
    assert week_start(date(2026, 11, 16)) == date(2026, 11, 16)
    assert week_start(date(2026, 11, 22)) == date(2026, 11, 16)
    assert week_start(date(2026, 11, 23)) == date(2026, 11, 23)


def test_weighted_sets() -> None:
    summary = summarize_session(
        DAY, ACTIVITY, [_log(8, "60"), _log(8, "62.5"), _log(6, "62.5"), _log(10, "55")]
    )

    assert summary.sets == 4
    assert summary.total_reps == 32
    assert summary.total_seconds is None
    assert summary.max_weight_kg == 62.5
    # 8×60 + 8×62,5 + 6×62,5 + 10×55
    assert summary.volume_kg == 1905.0
    # La mejor serie es la de más peso y, a igual peso, la de más repeticiones.
    assert (summary.best_set_reps, summary.best_set_seconds) == (8, None)


def test_uniform_sets_volume_is_sets_by_reps_by_weight() -> None:
    summary = summarize_session(DAY, ACTIVITY, [_log(8, "57.5")] * 3)

    assert summary.volume_kg == 3 * 8 * 57.5


def test_bodyweight_sets_have_no_weight_or_volume() -> None:
    summary = summarize_session(DAY, ACTIVITY, [_log(12), _log(15), _log(10)])

    assert (summary.max_weight_kg, summary.volume_kg) == (None, None)
    assert summary.total_reps == 37
    assert summary.best_set_reps == 15


def test_mixed_bodyweight_and_weighted_sets() -> None:
    summary = summarize_session(DAY, ACTIVITY, [_log(12), _log(8, "10")])

    assert summary.max_weight_kg == 10.0
    assert summary.volume_kg == 80.0
    assert summary.best_set_reps == 8


def test_seconds_sets() -> None:
    summary = summarize_session(DAY, ACTIVITY, [_log(seconds=45), _log(seconds=60)])

    assert (summary.total_reps, summary.total_seconds) == (None, 105)
    assert (summary.max_weight_kg, summary.volume_kg) == (None, None)
    assert (summary.best_set_reps, summary.best_set_seconds) == (None, 60)


def test_weighted_seconds_sets_have_no_volume() -> None:
    summary = summarize_session(
        DAY, ACTIVITY, [_log(seconds=40, weight="24"), _log(seconds=30, weight="32")]
    )

    assert summary.max_weight_kg == 32.0
    assert summary.volume_kg is None
    assert summary.best_set_seconds == 30
