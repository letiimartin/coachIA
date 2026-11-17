import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.integrations.wahoo.mapper import WahooMappingError, map_workout, sport_for
from app.models import Sport

FIXTURES = Path(__file__).parent / "fixtures" / "wahoo"


def load_fixture(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return data


def _ride() -> tuple[dict[str, Any], dict[str, Any]]:
    workout = load_fixture("workouts_page_1.json")["workouts"][1]
    return workout, workout["workout_summary"]


def test_map_workout_converts_units_to_table_columns() -> None:
    workout, summary = _ride()

    mapped = map_workout(workout, summary)

    assert mapped.external_id == "56519"
    values = mapped.values
    assert values["sport"] == Sport.CYCLING
    assert values["sub_sport"] == "biking_road"
    assert values["title"] == "Friday Fun"
    assert values["start_at"] == datetime(2015, 8, 12, 9, 0, tzinfo=UTC)
    assert values["timezone"] == "America/Denver"
    assert values["elapsed_s"] == 275
    assert values["moving_s"] == 179
    assert values["distance_m"] == Decimal("24909.7")
    assert values["ascent_m"] == Decimal("450.0")
    assert values["calories"] == 1500
    assert values["avg_hr"] == 100
    assert values["max_hr"] is None  # Wahoo no documenta la FC máxima.
    assert values["avg_power_w"] == 95
    assert values["normalized_power_w"] == 150
    assert values["avg_cadence"] == 50
    assert values["avg_speed_mps"] == Decimal("10.750")


def test_map_workout_keeps_original_response_and_no_derived_metrics() -> None:
    workout, summary = _ride()

    values = map_workout(workout, summary).values

    assert values["raw"] == workout
    assert values["raw"]["workout_summary"]["power_bike_tss_last"] == "304.90"
    # La carga la calcula el motor de métricas, no el sync.
    assert not {"load", "load_method", "intensity_factor"} & values.keys()


def test_map_workout_embeds_separately_fetched_summary_in_raw() -> None:
    workout = load_fixture("workouts_page_2.json")["workouts"][0]
    summary = load_fixture("workout_summary.json")

    values = map_workout(workout, summary).values

    assert values["raw"]["workout_summary"] == summary
    assert values["raw"]["id"] == 56400
    assert values["sport"] == Sport.TRAIL_RUNNING


def test_zero_sensor_values_mean_no_sensor() -> None:
    workout = load_fixture("workouts_page_2.json")["workouts"][0]

    values = map_workout(workout, load_fixture("workout_summary.json")).values

    assert values["avg_power_w"] is None
    assert values["normalized_power_w"] is None
    assert values["avg_hr"] == 148
    assert values["avg_cadence"] == 82


@pytest.mark.parametrize("bad", [None, "", "abc", "-5.00", "NaN", True])
def test_invalid_numbers_become_null(bad: Any) -> None:
    workout, _ = _ride()

    values = map_workout(workout, {"distance_accum": bad, "heart_rate_avg": bad}).values

    assert values["distance_m"] is None
    assert values["avg_hr"] is None


def test_title_falls_back_to_summary_name_and_empty_summary_fields_are_null() -> None:
    workout, _ = _ride()
    workout = {**workout, "name": None}

    values = map_workout(workout, {"name": "Easy Ride"}).values

    assert values["title"] == "Easy Ride"
    assert values["timezone"] is None
    assert values["elapsed_s"] is None


@pytest.mark.parametrize(
    ("type_id", "sport", "sub_sport"),
    [
        (0, Sport.CYCLING, "biking"),
        (61, Sport.CYCLING, "biking_indoor_trainer"),
        (68, Sport.CYCLING, "biking_indoor_virtual"),
        (1, Sport.RUNNING, "running"),
        (5, Sport.RUNNING, "running_treadmill"),
        (4, Sport.TRAIL_RUNNING, "running_trail"),
        (9, Sport.HIKING, "hiking"),
        (25, Sport.SWIMMING, "swimming_lap"),
        (17, Sport.OTHER, "biking_motocycling"),
        (66, Sport.OTHER, "yoga"),
        ("15", Sport.CYCLING, "biking_road"),
        (255, Sport.OTHER, "unknown"),
        (999, Sport.OTHER, "unknown"),
        (None, Sport.OTHER, "unknown"),
        ("x", Sport.OTHER, "unknown"),
    ],
)
def test_sport_by_workout_type_id(type_id: Any, sport: Sport, sub_sport: str) -> None:
    assert sport_for(type_id) == (sport, sub_sport)


@pytest.mark.parametrize(
    "workout",
    [
        {"starts": "2015-08-12T09:00:00.000Z"},
        {"id": 1},
        {"id": 1, "starts": "no es fecha"},
        {"id": 1, "starts": "2015-08-12T09:00:00"},  # sin zona horaria
    ],
)
def test_workout_without_id_or_valid_start_is_rejected(workout: dict[str, Any]) -> None:
    with pytest.raises(WahooMappingError):
        map_workout(workout, {})
