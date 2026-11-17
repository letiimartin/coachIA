import math

import pytest

from app.metrics.zones import (
    HrZoneSport,
    ZoneKind,
    hr_zones,
    lthr_field_for,
    pace_zones,
    power_zones,
    trail_hr_zones,
    zone_for,
    zone_model_for,
)
from app.models import AthleteThreshold, Sport


def test_power_zones_coggan_for_ftp_250() -> None:
    zones = power_zones(250)
    assert [z.code for z in zones] == ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7"]
    bounds = [(z.low, z.high) for z in zones]
    assert bounds == [
        (0.0, 137.5),
        (137.5, 187.5),
        (187.5, 225.0),
        (225.0, 262.5),
        (262.5, 300.0),
        (300.0, 375.0),
        (375.0, None),
    ]


def test_zones_are_contiguous() -> None:
    for zones in (power_zones(287), hr_zones(171), hr_zones(171, HrZoneSport.RUNNING)):
        for lower, upper in zip(zones, zones[1:], strict=False):
            assert lower.high == upper.low
        assert zones[0].low == 0
        assert zones[-1].high is None


def test_hr_zones_friel_cycling_for_lthr_170() -> None:
    zones = hr_zones(170)
    assert [z.code for z in zones] == ["Z1", "Z2", "Z3", "Z4", "Z5a", "Z5b", "Z5c"]
    lows = [z.low for z in zones]
    assert lows == pytest.approx([0, 137.7, 153.0, 159.8, 170.0, 175.1, 180.2])


def test_hr_zones_friel_running_for_lthr_170() -> None:
    lows = [z.low for z in hr_zones(170, HrZoneSport.RUNNING)]
    assert lows == pytest.approx([0, 144.5, 153.0, 161.5, 170.0, 175.1, 180.2])


def test_zone_for_value() -> None:
    zones = power_zones(250)
    assert zone_for(0, zones).code == "Z1"
    assert zone_for(200, zones).code == "Z3"
    assert zone_for(250, zones).code == "Z4"
    assert zone_for(1200, zones).code == "Z7"


def test_zone_for_boundary_belongs_to_upper_zone() -> None:
    zones = power_zones(250)
    assert zone_for(137.5, zones).code == "Z2"
    assert zone_for(137.49, zones).code == "Z1"
    assert zone_for(170, hr_zones(170)).code == "Z5a"


@pytest.mark.parametrize("bad", [0, -1, math.nan, math.inf])
def test_invalid_threshold_raises(bad: float) -> None:
    for build in (power_zones, hr_zones, pace_zones, trail_hr_zones):
        with pytest.raises(ValueError):
            build(bad)


# --- Ritmo de carrera (5 zonas de Friel) -------------------------------------------------------

PACE_4_52 = 292.0  # 4:52 /km


def test_pace_zones_for_threshold_4_52() -> None:
    zones = pace_zones(PACE_4_52)
    assert [z.code for z in zones] == ["Z1", "Z2", "Z3", "Z4", "Z5"]
    assert [z.number for z in zones] == [1, 2, 3, 4, 5]
    bounds = [(z.low, z.high) for z in zones]
    # En s/km: Z1 ≥ 376.68 (6:17), Z2 332.88-376.68, Z3 309.52-332.88, Z4 292-309.52, Z5 < 292.
    assert bounds == [
        (pytest.approx(376.68), None),
        (pytest.approx(332.88), pytest.approx(376.68)),
        (pytest.approx(309.52), pytest.approx(332.88)),
        (292.0, pytest.approx(309.52)),
        (0.0, 292.0),
    ]


def test_pace_zones_are_contiguous_from_slow_to_fast() -> None:
    zones = pace_zones(PACE_4_52)
    for slower, faster in zip(zones, zones[1:], strict=False):
        assert slower.low == faster.high
    assert zones[0].high is None
    assert zones[-1].low == 0


def test_pace_zone_for_values_and_boundaries() -> None:
    zones = pace_zones(PACE_4_52)
    assert zone_for(PACE_4_52, zones).code == "Z4"  # Al umbral exacto: Z4.
    assert zone_for(PACE_4_52 - 0.01, zones).code == "Z5"  # Más rápido que el umbral.
    assert zone_for(PACE_4_52 * 1.06, zones).code == "Z3"
    assert zone_for(PACE_4_52 * 1.14, zones).code == "Z2"
    assert zone_for(PACE_4_52 * 1.29, zones).code == "Z1"
    assert zone_for(PACE_4_52 * 1.29 - 0.01, zones).code == "Z2"
    assert zone_for(360.0, zones).code == "Z2"  # 6:00 /km.
    assert zone_for(900.0, zones).code == "Z1"
    assert zone_for(0, zones).code == "Z5"


# --- FC de trail (5 zonas de Friel) ----------------------------------------------------------


def test_trail_hr_zones_for_lthr_177() -> None:
    zones = trail_hr_zones(177)
    assert [z.code for z in zones] == ["Z1", "Z2", "Z3", "Z4", "Z5"]
    lows = [z.low for z in zones]
    assert lows == pytest.approx([0, 150.45, 159.3, 168.15, 177.0])
    assert zones[-1].high is None
    for lower, upper in zip(zones, zones[1:], strict=False):
        assert lower.high == upper.low


def test_trail_hr_zone_for_boundaries() -> None:
    zones = trail_hr_zones(177)
    assert zone_for(150.44, zones).code == "Z1"
    assert zone_for(150.45, zones).code == "Z2"
    assert zone_for(176.9, zones).code == "Z4"
    assert zone_for(177, zones).code == "Z5"
    assert zone_for(200, zones).code == "Z5"


# --- Referencia por disciplina -----------------------------------------------------------------


def test_zone_model_for_each_discipline() -> None:
    cycling = zone_model_for(Sport.CYCLING)
    running = zone_model_for(Sport.RUNNING)
    trail = zone_model_for(Sport.TRAIL_RUNNING)
    assert cycling is not None and running is not None and trail is not None
    assert (cycling.kind, cycling.threshold_field, cycling.unit) == (ZoneKind.POWER, "ftp_w", "W")
    assert (running.kind, running.threshold_field, running.unit) == (
        ZoneKind.PACE,
        "threshold_pace_s_per_km",
        "s/km",
    )
    assert (trail.kind, trail.threshold_field, trail.unit) == (
        ZoneKind.HEART_RATE,
        "running_lthr_bpm",
        "bpm",
    )
    assert cycling.zones(250) == power_zones(250)
    assert running.zones(PACE_4_52) == pace_zones(PACE_4_52)
    assert trail.zones(177) == trail_hr_zones(177)
    assert trail.zones(None) is None


@pytest.mark.parametrize("sport", [Sport.HIKING, Sport.STRENGTH, Sport.SWIMMING, Sport.OTHER])
def test_other_sports_have_no_zones(sport: Sport) -> None:
    assert zone_model_for(sport) is None


def test_lthr_per_discipline_and_threshold_fields_exist() -> None:
    assert lthr_field_for(Sport.CYCLING) == "cycling_lthr_bpm"
    assert lthr_field_for(Sport.RUNNING) == "running_lthr_bpm"
    # El trail usa el LTHR de carrera, y es el mismo que alimenta sus zonas.
    trail = zone_model_for(Sport.TRAIL_RUNNING)
    assert trail is not None and lthr_field_for(Sport.TRAIL_RUNNING) == trail.threshold_field
    columns = set(AthleteThreshold.__table__.columns.keys())
    for sport in Sport:
        assert lthr_field_for(sport) in columns
        model = zone_model_for(sport)
        assert model is None or model.threshold_field in columns


@pytest.mark.parametrize("bad", [-1, math.nan])
def test_zone_for_invalid_value_raises(bad: float) -> None:
    with pytest.raises(ValueError):
        zone_for(bad, power_zones(250))


def test_zone_for_without_zones_raises() -> None:
    with pytest.raises(ValueError):
        zone_for(100, [])
