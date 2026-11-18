"""Detección del intervalo del test de FTP de 20 minutos (series sintéticas a 1 Hz)."""

import pytest

from app.metrics.tests import (
    FTP_20MIN_DURATION_S,
    ActivityTooShortError,
    InsufficientDataError,
    NoPowerDataError,
    QualityWarningCode,
    Sample,
    ThresholdProtocol,
    analyze_ftp_20min,
    normalized_power,
)


def _series(*blocks: tuple[int, float | None], hr: float | None = 150.0) -> list[Sample]:
    """Bloques consecutivos de (segundos, vatios) a 1 Hz."""
    samples: list[Sample] = []
    offset = 0
    for duration, watts in blocks:
        for _ in range(duration):
            samples.append(Sample(offset_s=offset, power_w=watts, heart_rate_bpm=hr))
            offset += 1
    return samples


def _codes(samples: list[Sample]) -> set[QualityWarningCode]:
    return {warning.code for warning in analyze_ftp_20min(samples).warnings}


def test_clean_test_detects_the_block_and_proposes_95_percent() -> None:
    samples = _series((900, 150), (1200, 250), (600, 120))
    samples = [
        Sample(s.offset_s, s.power_w, 170.0 if 900 <= s.offset_s < 2100 else 130.0) for s in samples
    ]
    samples[1500] = Sample(1500, 250, 182.0)

    result = analyze_ftp_20min(samples)

    assert result.protocol is ThresholdProtocol.FTP_20MIN
    assert (result.start_offset_s, result.end_offset_s) == (900, 2100)
    assert result.avg_power_w == pytest.approx(250)
    assert result.normalized_power_w == pytest.approx(250)
    assert result.variability_index == pytest.approx(1.0)
    assert result.proposed_ftp_w == 238  # 0.95 · 250 = 237.5 → 238
    assert result.avg_hr_bpm == pytest.approx(170 + 12 / 1200)
    assert result.max_hr_bpm == 182
    assert result.valid_data_pct == 100
    assert result.warmup_s == 900
    assert result.warnings == ()


def test_best_block_wins_over_an_earlier_weaker_one() -> None:
    samples = _series((600, 100), (1200, 220), (300, 100), (1200, 260), (300, 100))
    result = analyze_ftp_20min(samples)
    assert result.start_offset_s == 2100
    assert result.proposed_ftp_w == 247  # 0.95 · 260


def test_block_not_aligned_with_effort_takes_the_best_20_minutes() -> None:
    # Esfuerzo de 25 min con los últimos 5 más fuertes: el mejor bloque acaba al final.
    samples = _series((900, 150), (1200, 240), (300, 300), (300, 100))
    result = analyze_ftp_20min(samples)
    assert (result.start_offset_s, result.end_offset_s) == (900 + 300, 900 + 1500)
    assert result.avg_power_w == pytest.approx((900 * 240 + 300 * 300) / 1200)


def test_short_dropouts_are_filled_without_warning() -> None:
    samples = _series((900, 150), (1200, 250), (300, 100))
    # Huecos de 3 s (sin registro) dentro del bloque: se rellenan con el valor anterior.
    samples = [s for s in samples if not 1200 <= s.offset_s < 1203]
    result = analyze_ftp_20min(samples)
    assert result.avg_power_w == pytest.approx(250)
    assert result.valid_data_pct == 100
    assert result.warnings == ()


def test_long_gap_inside_the_block_is_not_interpolated_and_warns() -> None:
    samples = _series((900, 150), (1200, 250), (300, 100))
    # Pausa del registro de 60 s en mitad del test: cuenta como 0 W, no se interpola.
    samples = [s for s in samples if not 1500 <= s.offset_s < 1560]
    result = analyze_ftp_20min(samples)
    assert result.avg_power_w < 250
    assert result.valid_data_pct < 100
    assert QualityWarningCode.DATA_GAPS in {w.code for w in result.warnings}


def test_zero_power_pause_inside_the_block_warns() -> None:
    samples = _series((900, 150), (500, 260), (30, 0), (670, 260), (300, 100))
    codes = _codes(samples)
    assert QualityWarningCode.PAUSES in codes
    assert QualityWarningCode.DATA_GAPS not in codes


def test_short_zero_power_stretch_does_not_warn_as_pause() -> None:
    samples = _series((900, 150), (600, 250), (5, 0), (595, 250), (300, 100))
    assert QualityWarningCode.PAUSES not in _codes(samples)


def test_high_variability_warns() -> None:
    blocks: list[tuple[int, float | None]] = [(900, 150)]
    blocks += [(60, 400), (60, 100)] * 10
    blocks += [(300, 100)]
    assert QualityWarningCode.HIGH_VARIABILITY in _codes(_series(*blocks))


def test_test_without_warmup_warns() -> None:
    samples = _series((1200, 250), (900, 120))
    result = analyze_ftp_20min(samples)
    assert result.start_offset_s == 0
    assert {w.code for w in result.warnings} == {QualityWarningCode.NO_WARMUP}


def test_offsets_start_at_the_first_sample() -> None:
    samples = [Sample(s.offset_s + 30, s.power_w) for s in _series((900, 150), (1200, 250))]
    result = analyze_ftp_20min(samples)
    assert (result.start_offset_s, result.warmup_s) == (930, 900)
    assert result.avg_hr_bpm is None and result.max_hr_bpm is None


def test_activity_shorter_than_20_minutes_fails() -> None:
    with pytest.raises(ActivityTooShortError):
        analyze_ftp_20min(_series((FTP_20MIN_DURATION_S - 1, 250)))
    with pytest.raises(ActivityTooShortError):
        analyze_ftp_20min([])


def test_activity_without_power_fails() -> None:
    with pytest.raises(NoPowerDataError):
        analyze_ftp_20min(_series((3000, None)))
    with pytest.raises(NoPowerDataError):
        analyze_ftp_20min(_series((3000, 0)))


def test_block_with_mostly_missing_power_fails() -> None:
    samples = _series((500, 300), (2500, None))
    with pytest.raises(InsufficientDataError):
        analyze_ftp_20min(samples)


def test_invalid_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="no negativos"):
        analyze_ftp_20min(_series((1200, -5)))


def test_normalized_power_of_constant_series_is_the_value() -> None:
    assert normalized_power([200.0] * 120) == pytest.approx(200)
    assert normalized_power([100.0, 300.0]) == pytest.approx(200)
    assert normalized_power([150.0] * 60 + [350.0] * 60) > 250
