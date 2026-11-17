"""Contrato de perfil, umbrales, disponibilidad y calendario (#10).

Los endpoints existen, exigen JWT, validan la entrada y, de momento, responden 501.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.metrics.zones import HrZoneSport, hr_zones, power_zones
from app.schemas.athlete import (
    CurrentThresholdOut,
    ProfileOut,
    ProfilePatch,
    ThresholdCreate,
    ThresholdOut,
    WeekAvailability,
    ZoneOut,
)
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventOut,
    CalendarEventPatch,
    RaceCreate,
    RacePatch,
)
from tests.conftest import TokenFactory

EVENT_ID = "3f2a1b4c-5d6e-4f70-8a9b-0c1d2e3f4a5b"


def _example(model: type[BaseModel], index: int = 0) -> Any:
    examples = model.model_json_schema()["examples"]
    return examples[index]


VALID_REQUESTS: list[tuple[str, str, Any]] = [
    ("GET", "/v1/athlete/profile", None),
    ("PATCH", "/v1/athlete/profile", _example(ProfilePatch)),
    ("GET", "/v1/athlete/thresholds", None),
    ("POST", "/v1/athlete/thresholds", _example(ThresholdCreate)),
    ("GET", "/v1/athlete/thresholds/current", None),
    ("GET", "/v1/athlete/thresholds/current?on=2026-11-17", None),
    ("GET", "/v1/athlete/availability", None),
    ("PUT", "/v1/athlete/availability", _example(WeekAvailability)),
    ("GET", "/v1/calendar/events?from=2026-11-01&to=2026-11-30", None),
    ("POST", "/v1/calendar/events", _example(CalendarEventCreate, 0)),
    ("POST", "/v1/calendar/events", _example(CalendarEventCreate, 1)),
    ("PATCH", f"/v1/calendar/events/{EVENT_ID}", _example(CalendarEventPatch)),
    ("DELETE", f"/v1/calendar/events/{EVENT_ID}", None),
]


def _ids(requests: list[tuple[str, str, Any]]) -> list[str]:
    return [f"{method} {path}" for method, path, _ in requests]


@pytest.mark.parametrize(("method", "path", "body"), VALID_REQUESTS, ids=_ids(VALID_REQUESTS))
def test_endpoints_require_jwt(client: TestClient, method: str, path: str, body: Any) -> None:
    response = client.request(method, path, json=body)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(("method", "path", "body"), VALID_REQUESTS, ids=_ids(VALID_REQUESTS))
def test_endpoints_are_declared_but_not_implemented(
    client: TestClient, make_token: TokenFactory, method: str, path: str, body: Any
) -> None:
    headers = {"Authorization": f"Bearer {make_token()}"}

    response = client.request(method, path, json=body, headers=headers)

    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_implemented"


_DAY = {"max_minutes": 60, "sports": ["cycling"], "preferred_time": "any"}
INVALID_REQUESTS: list[tuple[str, str, Any]] = [
    # Perfil
    ("PATCH", "/v1/athlete/profile", {"height_cm": 99}),
    ("PATCH", "/v1/athlete/profile", {"height_cm": 251}),
    ("PATCH", "/v1/athlete/profile", {"sex": "unknown"}),
    ("PATCH", "/v1/athlete/profile", {"timezone": "Mars/Olympus"}),
    ("PATCH", "/v1/athlete/profile", {"timezone": None}),
    ("PATCH", "/v1/athlete/profile", {"sports": ["cycling", "cycling"]}),
    ("PATCH", "/v1/athlete/profile", {"sports": ["padel"]}),
    ("PATCH", "/v1/athlete/profile", {"display_name": "x" * 121}),
    ("PATCH", "/v1/athlete/profile", {"birth_date": "2999-01-01"}),
    ("PATCH", "/v1/athlete/profile", {"unknown_field": 1}),
    # Umbrales
    ("POST", "/v1/athlete/thresholds", {"ftp_w": 250}),
    ("POST", "/v1/athlete/thresholds", {"effective_from": "2026-11-01"}),
    ("POST", "/v1/athlete/thresholds", {"effective_from": "2026-11-01", "ftp_w": 49}),
    ("POST", "/v1/athlete/thresholds", {"effective_from": "2026-11-01", "ftp_w": 701}),
    ("POST", "/v1/athlete/thresholds", {"effective_from": "2026-11-01", "lthr_bpm": 231}),
    ("POST", "/v1/athlete/thresholds", {"effective_from": "2026-11-01", "hr_max_bpm": 99}),
    ("POST", "/v1/athlete/thresholds", {"effective_from": "2026-11-01", "hr_rest_bpm": 24}),
    ("POST", "/v1/athlete/thresholds", {"effective_from": "2026-11-01", "weight_kg": 251}),
    (
        "POST",
        "/v1/athlete/thresholds",
        {"effective_from": "2026-11-01", "ftp_w": 200, "source": "x"},
    ),
    (
        "POST",
        "/v1/athlete/thresholds",
        {"effective_from": "2026-11-01", "hr_max_bpm": 120, "hr_rest_bpm": 120},
    ),
    ("GET", "/v1/athlete/thresholds/current?on=ayer", None),
    # Disponibilidad
    ("PUT", "/v1/athlete/availability", {"days": [{"weekday": i, **_DAY} for i in range(6)]}),
    ("PUT", "/v1/athlete/availability", {"days": [{"weekday": 0, **_DAY} for _ in range(7)]}),
    ("PUT", "/v1/athlete/availability", {"days": [{"weekday": i + 1, **_DAY} for i in range(7)]}),
    (
        "PUT",
        "/v1/athlete/availability",
        {"days": [{"weekday": i, **_DAY, "max_minutes": 1441} for i in range(7)]},
    ),
    (
        "PUT",
        "/v1/athlete/availability",
        {"days": [{"weekday": i, **_DAY, "preferred_time": "night"} for i in range(7)]},
    ),
    # Calendario
    ("GET", "/v1/calendar/events", None),
    ("GET", "/v1/calendar/events?from=2026-11-30&to=2026-11-01", None),
    ("GET", "/v1/calendar/events?from=2026-01-01&to=2027-01-02", None),
    (
        "POST",
        "/v1/calendar/events",
        {"kind": "party", "title": "x", "start_at": "2026-12-01T10:00:00Z"},
    ),
    (
        "POST",
        "/v1/calendar/events",
        {"kind": "social", "title": "", "start_at": "2026-12-01T10:00:00Z"},
    ),
    (
        "POST",
        "/v1/calendar/events",
        {"kind": "social", "title": "x", "start_at": "2026-12-01T10:00:00"},
    ),
    (
        "POST",
        "/v1/calendar/events",
        {
            "kind": "social",
            "title": "Cena",
            "start_at": "2026-12-01T20:00:00Z",
            "end_at": "2026-12-01T19:00:00Z",
        },
    ),
    (
        "POST",
        "/v1/calendar/events",
        {"kind": "social", "title": "Cena", "start_at": "2026-12-01T20:00:00Z", "race": {}},
    ),
    (
        "POST",
        "/v1/calendar/events",
        {
            "kind": "race",
            "title": "Carrera",
            "start_at": "2027-04-18T07:00:00Z",
            "race": {"priority": "D"},
        },
    ),
    (
        "POST",
        "/v1/calendar/events",
        {
            "kind": "race",
            "title": "Carrera",
            "start_at": "2027-04-18T07:00:00Z",
            "race": {"distance_m": -1},
        },
    ),
    (
        "POST",
        "/v1/calendar/events",
        {
            "kind": "race",
            "title": "Carrera",
            "start_at": "2027-04-18T07:00:00Z",
            "race": {"source_url": "no-es-una-url"},
        },
    ),
    ("PATCH", f"/v1/calendar/events/{EVENT_ID}", {"title": None}),
    ("PATCH", f"/v1/calendar/events/{EVENT_ID}", {"race": {"priority": None}}),
    ("PATCH", f"/v1/calendar/events/{EVENT_ID}", {"kind": "travel", "race": {"priority": "A"}}),
    ("PATCH", "/v1/calendar/events/no-es-un-uuid", {"title": "x"}),
    ("DELETE", "/v1/calendar/events/no-es-un-uuid", None),
]


@pytest.mark.parametrize(("method", "path", "body"), INVALID_REQUESTS, ids=_ids(INVALID_REQUESTS))
def test_invalid_input_is_rejected(
    client: TestClient, make_token: TokenFactory, method: str, path: str, body: Any
) -> None:
    headers = {"Authorization": f"Bearer {make_token()}"}

    response = client.request(method, path, json=body, headers=headers)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "model",
    [
        ProfileOut,
        ProfilePatch,
        ThresholdCreate,
        ThresholdOut,
        CurrentThresholdOut,
        WeekAvailability,
        RaceCreate,
        RacePatch,
        CalendarEventCreate,
        CalendarEventPatch,
        CalendarEventOut,
    ],
)
def test_schema_examples_are_valid(model: type[BaseModel]) -> None:
    """La app usa los ejemplos como datos de prueba: tienen que cumplir el contrato."""
    examples = model.model_json_schema()["examples"]

    assert examples
    for example in examples:
        model.model_validate(example)


def test_patch_distinguishes_omitted_from_null() -> None:
    patch = ProfilePatch.model_validate({"birth_date": None})

    assert patch.model_fields_set == {"birth_date"}
    assert patch.model_dump(exclude_unset=True) == {"birth_date": None}


def test_availability_days_are_sorted_by_weekday() -> None:
    days = [{"weekday": i} for i in (6, 5, 4, 3, 2, 1, 0)]

    week = WeekAvailability.model_validate({"days": days})

    assert [day.weekday for day in week.days] == list(range(7))


def test_zone_schema_matches_metrics_engine() -> None:
    zones = [
        *power_zones(250),
        *hr_zones(170, HrZoneSport.CYCLING),
        *hr_zones(170, HrZoneSport.RUNNING),
    ]

    for zone in zones:
        out = ZoneOut.from_zone(zone)
        assert (out.number, out.code, out.name, out.low, out.high) == (
            zone.number,
            zone.code,
            zone.name,
            zone.low,
            zone.high,
        )
