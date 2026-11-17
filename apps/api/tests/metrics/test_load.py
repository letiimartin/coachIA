import math

import pytest

from app.metrics.load import (
    LoadResult,
    activity_load,
    hr_tss,
    intensity_factor_for,
    pace_s_per_km,
    power_tss,
    run_tss,
)
from app.models import LoadMethod


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
    assert activity_load(0, avg_hr_bpm=150, lthr_bpm=170) == LoadResult(
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


def test_best_method_prefers_power_then_hr_then_pace() -> None:
    everything = {
        "normalized_power_w": 200,
        "ftp_w": 250,
        "avg_hr_bpm": 150,
        "lthr_bpm": 170,
        "avg_speed_mps": 3.5,
        "threshold_pace_s_per_km": 270,
    }
    result = activity_load(3600, **everything)
    assert result is not None and result.method is LoadMethod.POWER

    no_ftp = {**everything, "ftp_w": None}
    result = activity_load(3600, **no_ftp)
    assert result is not None and result.method is LoadMethod.HEART_RATE

    no_hr = {**no_ftp, "avg_hr_bpm": None}
    result = activity_load(3600, **no_hr)
    assert result is not None and result.method is LoadMethod.PACE
    assert result.load == pytest.approx((270 / (1000 / 3.5)) ** 2 * 100)


def test_best_method_none_available() -> None:
    assert activity_load(3600) is None
    assert activity_load(3600, normalized_power_w=200, avg_hr_bpm=150) is None


def test_result_unpacks_as_contract_tuple() -> None:
    load, method, intensity = power_tss(3600, 250, 250) or (0.0, None, None)
    assert (load, method, intensity) == (100.0, LoadMethod.POWER, 1.0)
