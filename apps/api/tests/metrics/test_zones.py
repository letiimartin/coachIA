import math

import pytest

from app.metrics.zones import HrZoneSport, hr_zones, power_zones, zone_for


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
    with pytest.raises(ValueError):
        power_zones(bad)
    with pytest.raises(ValueError):
        hr_zones(bad)


@pytest.mark.parametrize("bad", [-1, math.nan])
def test_zone_for_invalid_value_raises(bad: float) -> None:
    with pytest.raises(ValueError):
        zone_for(bad, power_zones(250))


def test_zone_for_without_zones_raises() -> None:
    with pytest.raises(ValueError):
        zone_for(100, [])
