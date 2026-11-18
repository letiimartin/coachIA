import math

import pytest

from app.metrics.load import (
    LOAD_RULES,
    LoadResult,
    activity_load,
    counts_in_daily_load,
    hr_tss,
    intensity_factor_for,
    pace_s_per_km,
    power_tss,
    run_tss,
    session_rpe_load,
)
from app.models import LoadMethod, Sport
from app.models.activity import Activity


def test_one_hour_at_threshold_is_100() -> None:
    assert power_tss(3600, 250, 250) == LoadResult(100.0, LoadMethod.POWER, 1.0)
    assert hr_tss(3600, 165, 165) == LoadResult(100.0, LoadMethod.HEART_RATE, None)
    assert run_tss(3600, 240, 240) == LoadResult(100.0, LoadMethod.PACE, None)


def test_power_tss_known_value() -> None:
    # 2 h a NP 200 W con FTP 250 W: IF 0.8 -> 2 · 0.64 · 100 = 128.
    result = power_tss(7200, 200, 250)
    assert result is not None
    assert result.load == pytest.approx(128.0)
    assert result.method is LoadMethod.POWER
    assert result.intensity_factor == pytest.approx(0.8)


def test_power_tss_matches_coggan_formula() -> None:
    s, np_w, ftp = 5400, 230, 260
    intensity = np_w / ftp
    expected = (s * np_w * intensity) / (ftp * 3600) * 100
    result = power_tss(s, np_w, ftp)
    assert result is not None
    assert result.load == pytest.approx(expected)


def test_hr_tss_known_value() -> None:
    # 1 h 30 a 150 ppm con LTHR 170: IF 0.882 -> 1.5 · 0.7785 · 100 = 116.8.
    result = hr_tss(5400, 150, 170)
    assert result is not None
    assert result.load == pytest.approx(1.5 * (150 / 170) ** 2 * 100)
    assert result.method is LoadMethod.HEART_RATE


def test_run_tss_known_value() -> None:
    # 1 h a 5:00/km con umbral 4:30/km: IF 0.9 -> 81.
    result = run_tss(3600, 300, 270)
    assert result is not None
    assert result.load == pytest.approx(81.0)
    assert result.intensity_factor is None  # De momento el IF sólo se publica con potencia.
    assert result.method is LoadMethod.PACE


def test_faster_than_threshold_pace_counts_more_than_an_hour_at_threshold() -> None:
    result = run_tss(3600, 240, 270)
    assert result is not None
    assert result.load == pytest.approx(1.125**2 * 100)


def test_intensity_factor_is_published_per_method() -> None:
    assert intensity_factor_for(LoadMethod.POWER, 0.85) == pytest.approx(0.85)
    for method in (LoadMethod.HEART_RATE, LoadMethod.PACE, LoadMethod.RPE):
        assert intensity_factor_for(method, 0.85) is None


def test_zero_duration_gives_zero_load() -> None:
    result = power_tss(0, 200, 250)
    assert result == LoadResult(0.0, LoadMethod.POWER, pytest.approx(0.8))
    assert activity_load(Sport.CYCLING, 0, avg_hr_bpm=150, lthr_bpm=170) == LoadResult(
        0.0, LoadMethod.HEART_RATE, None
    )


@pytest.mark.parametrize("ftp", [None, 0])
def test_without_ftp_power_tss_is_none(ftp: float | None) -> None:
    assert power_tss(3600, 200, ftp) is None


def test_missing_activity_data_is_none() -> None:
    assert power_tss(3600, None, 250) is None
    assert hr_tss(3600, None, 170) is None
    assert hr_tss(3600, 150, None) is None
    assert run_tss(3600, None, 270) is None
    assert run_tss(3600, 300, None) is None


@pytest.mark.parametrize("duration", [-1, math.nan, math.inf])
def test_invalid_duration_raises(duration: float) -> None:
    with pytest.raises(ValueError):
        power_tss(duration, 200, 250)


def test_negative_threshold_raises() -> None:
    with pytest.raises(ValueError):
        hr_tss(3600, 150, -170)


def test_pace_from_speed() -> None:
    assert pace_s_per_km(4.0) == pytest.approx(250.0)
    assert pace_s_per_km(None) is None
    assert pace_s_per_km(0) is None


EVERYTHING = {
    "normalized_power_w": 200,
    "ftp_w": 250,
    "avg_hr_bpm": 150,
    "lthr_bpm": 170,
    "avg_speed_mps": 3.5,
    "threshold_pace_s_per_km": 270,
}


def test_cycling_uses_power_then_hr() -> None:
    result = activity_load(Sport.CYCLING, 3600, **EVERYTHING, rpe=7)
    assert result is not None and result.method is LoadMethod.POWER

    no_ftp = {**EVERYTHING, "ftp_w": None}
    result = activity_load(Sport.CYCLING, 3600, **no_ftp, rpe=7)
    assert result is not None and result.method is LoadMethod.HEART_RATE
    assert result.load == pytest.approx((150 / 170) ** 2 * 100)

    # Sin FC: el paso RPE no tiene fórmula aprobada y el ritmo nunca cuenta en ciclismo.
    no_hr = {**no_ftp, "avg_hr_bpm": None}
    assert activity_load(Sport.CYCLING, 3600, **no_hr, rpe=7) is None


def test_running_uses_pace_first() -> None:
    result = activity_load(Sport.RUNNING, 3600, **EVERYTHING, rpe=7)
    assert result is not None and result.method is LoadMethod.PACE
    assert result.load == pytest.approx((270 / (1000 / 3.5)) ** 2 * 100)


@pytest.mark.parametrize(
    "missing", [{"avg_speed_mps": None}, {"avg_speed_mps": 0}, {"threshold_pace_s_per_km": None}]
)
def test_running_without_valid_pace_falls_back_to_hr(missing: dict[str, None]) -> None:
    # P. ej. en cinta sin sensor de velocidad pero con pulso.
    result = activity_load(Sport.RUNNING, 3600, **{**EVERYTHING, **missing})
    assert result is not None and result.method is LoadMethod.HEART_RATE
    assert result.load == pytest.approx((150 / 170) ** 2 * 100)


def test_running_without_pace_and_hr_has_no_load_even_with_rpe() -> None:
    nothing = {**EVERYTHING, "avg_speed_mps": None, "avg_hr_bpm": None}
    assert activity_load(Sport.RUNNING, 3600, **nothing, rpe=7) is None


def test_trail_uses_hr_never_power_or_pace() -> None:
    result = activity_load(Sport.TRAIL_RUNNING, 3600, **EVERYTHING)
    assert result is not None and result.method is LoadMethod.HEART_RATE
    assert result.load == pytest.approx((150 / 170) ** 2 * 100)


def test_trail_with_pace_but_without_hr_does_not_use_pace() -> None:
    assert activity_load(Sport.TRAIL_RUNNING, 3600, **{**EVERYTHING, "avg_hr_bpm": None}) is None
    assert activity_load(Sport.TRAIL_RUNNING, 3600, **{**EVERYTHING, "lthr_bpm": None}) is None


def test_trail_without_hr_and_without_rpe_formula_has_no_load() -> None:
    assert activity_load(Sport.TRAIL_RUNNING, 3600, avg_speed_mps=3.0) is None
    assert activity_load(Sport.TRAIL_RUNNING, 3600, avg_speed_mps=3.0, rpe=8) is None


def test_endurance_rpe_step_is_pending_a_formula() -> None:
    for sport in (Sport.CYCLING, Sport.RUNNING, Sport.TRAIL_RUNNING):
        assert LOAD_RULES[sport].methods[-1] is LoadMethod.RPE
        assert activity_load(sport, 3600, rpe=10) is None


@pytest.mark.parametrize("sport", [Sport.HIKING, Sport.SWIMMING, Sport.OTHER])
def test_registered_only_sports_never_get_a_load(sport: Sport) -> None:
    # Ni con FC y LTHR (de carrera o de ciclismo), ni con potencia, ritmo o RPE.
    assert LOAD_RULES[sport].registered_only
    assert activity_load(sport, 3600, **EVERYTHING, rpe=7) is None
    assert not counts_in_daily_load(sport, LoadMethod.HEART_RATE)


# --- Fuerza: session RPE --------------------------------------------------------------------


def test_strength_with_hr_and_without_rpe_has_no_load() -> None:
    assert activity_load(Sport.STRENGTH, 3600, **EVERYTHING) is None


def test_strength_with_rpe_is_minutes_times_rpe() -> None:
    result = activity_load(Sport.STRENGTH, 3600, **EVERYTHING, rpe=7)
    assert result == LoadResult(420.0, LoadMethod.SESSION_RPE, None)
    # Sin tiempo en movimiento, el total.
    result = activity_load(Sport.STRENGTH, None, elapsed_s=2700, rpe=6)
    assert result == LoadResult(270.0, LoadMethod.SESSION_RPE, None)
    assert activity_load(Sport.STRENGTH, None, rpe=6) is None


def test_session_rpe_load_validates() -> None:
    assert session_rpe_load(3600, None) is None
    assert session_rpe_load(None, 5) is None
    assert session_rpe_load(0, 5) == LoadResult(0.0, LoadMethod.SESSION_RPE, None)
    for bad in (0, 11):
        with pytest.raises(ValueError):
            session_rpe_load(3600, bad)
    with pytest.raises(ValueError):
        session_rpe_load(-1, 5)


def test_session_rpe_is_never_used_outside_strength() -> None:
    for sport, rule in LOAD_RULES.items():
        assert (LoadMethod.SESSION_RPE in rule.methods) is (sport is Sport.STRENGTH)


def test_only_endurance_counts_in_daily_load() -> None:
    for sport in (Sport.CYCLING, Sport.RUNNING, Sport.TRAIL_RUNNING):
        assert counts_in_daily_load(sport, LoadMethod.POWER)
        assert not counts_in_daily_load(sport, LoadMethod.SESSION_RPE)
    # Una carga TSS antigua de fuerza tampoco suma.
    assert not counts_in_daily_load(Sport.STRENGTH, LoadMethod.HEART_RATE)
    assert not counts_in_daily_load(Sport.STRENGTH, LoadMethod.SESSION_RPE)
    assert not LOAD_RULES[Sport.STRENGTH].registered_only
    for sport in (Sport.CYCLING, Sport.RUNNING, Sport.TRAIL_RUNNING):
        assert not LOAD_RULES[sport].registered_only


def test_every_sport_has_a_rule() -> None:
    assert set(LOAD_RULES) == set(Sport)
    assert Activity.__table__.c.rpe is not None


def test_no_method_available() -> None:
    for sport in Sport:
        assert activity_load(sport, 3600) is None
        assert activity_load(sport, None) is None


def test_activity_load_validates_duration() -> None:
    with pytest.raises(ValueError):
        activity_load(Sport.RUNNING, -1)


def test_result_unpacks_as_contract_tuple() -> None:
    load, method, intensity = power_tss(3600, 250, 250) or (0.0, None, None)
    assert (load, method, intensity) == (100.0, LoadMethod.POWER, 1.0)
