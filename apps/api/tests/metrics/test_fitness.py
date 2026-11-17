import math
from datetime import date, timedelta

import pytest

from app.metrics.fitness import fill_daily_load, fitness_series

D0 = date(2026, 1, 1)


def test_single_day_from_zero() -> None:
    [day] = fitness_series({D0: 100.0})
    assert day.day == D0
    assert day.ctl == pytest.approx(100 / 42)
    assert day.atl == pytest.approx(100 / 7)
    assert day.tsb == 0.0  # TSB con los valores del día anterior (aún sin historia).


def test_gaps_are_filled_with_zero() -> None:
    series = fitness_series({D0: 100.0, D0 + timedelta(days=3): 50.0})
    assert [d.day for d in series] == [D0 + timedelta(days=i) for i in range(4)]
    assert [d.load for d in series] == [100.0, 0.0, 0.0, 50.0]
    # Sin carga, CTL y ATL decaen por (1 - 1/τ) cada día.
    assert series[2].ctl == pytest.approx(series[0].ctl * (41 / 42) ** 2)
    assert series[2].atl == pytest.approx(series[0].atl * (6 / 7) ** 2)


def test_constant_load_converges_to_that_load() -> None:
    loads = {D0 + timedelta(days=i): 60.0 for i in range(400)}
    last = fitness_series(loads)[-1]
    assert last.ctl == pytest.approx(60.0 * (1 - (41 / 42) ** 400))
    assert last.ctl == pytest.approx(60.0, abs=0.01)
    assert last.atl == pytest.approx(60.0, abs=1e-9)
    assert last.tsb == pytest.approx(0.0, abs=0.01)


def test_known_values_after_a_week() -> None:
    loads = {D0 + timedelta(days=i): 100.0 for i in range(7)}
    series = fitness_series(loads)
    last = series[-1]
    assert last.ctl == pytest.approx(100 * (1 - (41 / 42) ** 7))
    assert last.atl == pytest.approx(100 * (1 - (6 / 7) ** 7))
    previous = series[-2]
    assert last.tsb == pytest.approx(previous.ctl - previous.atl)


def test_tsb_uses_previous_day_values() -> None:
    series = fitness_series({D0: 100.0, D0 + timedelta(days=1): 0.0})
    assert series[0].tsb == 0.0
    assert series[1].tsb == pytest.approx(series[0].ctl - series[0].atl)


def test_explicit_range_and_initial_state() -> None:
    series = fitness_series(
        {D0 - timedelta(days=5): 500.0},
        start=D0,
        end=D0 + timedelta(days=1),
        initial_ctl=42.0,
        initial_atl=70.0,
    )
    assert len(series) == 2
    assert [d.load for d in series] == [0.0, 0.0]  # La carga fuera del rango se ignora.
    assert series[0].ctl == pytest.approx(41.0)
    assert series[0].atl == pytest.approx(60.0)
    assert series[0].tsb == pytest.approx(42.0 - 70.0)  # Estado inicial (día anterior).
    assert series[1].tsb == pytest.approx(41.0 - 60.0)


def test_empty_series() -> None:
    assert fitness_series({}) == []


def test_empty_days_with_explicit_range() -> None:
    series = fitness_series({}, start=D0, end=D0 + timedelta(days=2), initial_ctl=50.0)
    assert [d.load for d in series] == [0.0, 0.0, 0.0]
    assert series[-1].ctl == pytest.approx(50 * (41 / 42) ** 3)


def test_fill_daily_load() -> None:
    assert fill_daily_load({D0 + timedelta(days=1): 30.0}, D0, D0 + timedelta(days=2)) == [
        (D0, 0.0),
        (D0 + timedelta(days=1), 30.0),
        (D0 + timedelta(days=2), 0.0),
    ]


def test_start_after_end_raises() -> None:
    with pytest.raises(ValueError):
        fitness_series({}, start=D0, end=D0 - timedelta(days=1))


@pytest.mark.parametrize("bad", [-1.0, math.nan])
def test_invalid_load_raises(bad: float) -> None:
    with pytest.raises(ValueError):
        fitness_series({D0: bad})


def test_invalid_time_constant_raises() -> None:
    with pytest.raises(ValueError):
        fitness_series({D0: 10.0}, ctl_days=0)
