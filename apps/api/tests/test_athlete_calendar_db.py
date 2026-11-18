"""Perfil, umbrales, disponibilidad y calendario contra Postgres (#16)."""

import uuid
from collections.abc import Iterator
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from app.core.security import TokenVerifier
from app.db.session import Database
from app.main import create_app
from app.metrics.zones import HrZoneSport, hr_zones, pace_zones, power_zones, trail_hr_zones
from app.models import AthleteThreshold, AvailabilitySlot, Race
from app.schemas.athlete import WeekAvailability
from tests.conftest import (
    FakeJWKSClient,
    TokenFactory,
    database_url_for_tests,
    make_settings,
    requires_db,
)

pytestmark = requires_db

Headers = dict[str, str]


@pytest.fixture
def db_client(engine: Engine, ec_private_key: ec.EllipticCurvePrivateKey) -> Iterator[TestClient]:
    settings = make_settings()
    app: FastAPI = create_app(
        settings,
        token_verifier=TokenVerifier(settings, FakeJWKSClient(ec_private_key.public_key())),
        database=Database(database_url_for_tests()),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def other_user_id(engine: Engine) -> Iterator[uuid.UUID]:
    new_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": new_id})
    yield new_id
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": new_id})


@pytest.fixture
def headers(make_token: TokenFactory, user_id: uuid.UUID) -> Headers:
    return {"Authorization": f"Bearer {make_token(sub=str(user_id))}"}


@pytest.fixture
def other_headers(make_token: TokenFactory, other_user_id: uuid.UUID) -> Headers:
    return {"Authorization": f"Bearer {make_token(sub=str(other_user_id))}"}


def _count(engine: Engine, model: Any, user_id: uuid.UUID) -> int:
    with Session(engine) as session:
        return (
            session.scalar(select(func.count()).select_from(model).where(model.user_id == user_id))
            or 0
        )


# --- Perfil ----------------------------------------------------------------------------------


def test_get_profile_creates_it_with_defaults(
    db_client: TestClient, headers: Headers, user_id: uuid.UUID
) -> None:
    response = db_client.get("/v1/athlete/profile", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(user_id)
    assert body["timezone"] == "Europe/Madrid"
    assert body["sports"] == []
    assert body["preferences"] == {}
    assert body["display_name"] is None
    assert db_client.get("/v1/athlete/profile", headers=headers).json() == body


def test_patch_profile_changes_only_sent_fields(db_client: TestClient, headers: Headers) -> None:
    first = db_client.patch(
        "/v1/athlete/profile",
        headers=headers,
        json={
            "display_name": "Leti",
            "height_cm": 168.5,
            "sex": "female",
            "sports": ["cycling", "trail_running"],
            "preferences": {"units": "metric", "language": "es"},
        },
    )
    assert first.status_code == 200, first.text

    second = db_client.patch(
        "/v1/athlete/profile",
        headers=headers,
        json={"height_cm": None, "timezone": "Atlantic/Canary", "preferences": {"units": "x"}},
    )

    assert second.status_code == 200, second.text
    body = second.json()
    assert body["display_name"] == "Leti"
    assert body["sex"] == "female"
    assert body["sports"] == ["cycling", "trail_running"]
    assert body["height_cm"] is None
    assert body["timezone"] == "Atlantic/Canary"
    assert body["preferences"] == {"units": "x"}  # se sustituye, no se fusiona
    assert body["updated_at"] >= first.json()["updated_at"]
    assert db_client.get("/v1/athlete/profile", headers=headers).json() == body


def test_profiles_are_isolated(
    db_client: TestClient, headers: Headers, other_headers: Headers, other_user_id: uuid.UUID
) -> None:
    db_client.patch("/v1/athlete/profile", headers=headers, json={"display_name": "Leti"})

    other = db_client.get("/v1/athlete/profile", headers=other_headers).json()

    assert other["user_id"] == str(other_user_id)
    assert other["display_name"] is None


# --- Umbrales --------------------------------------------------------------------------------


def _threshold(effective_from: str, **values: Any) -> dict[str, Any]:
    return {"effective_from": effective_from, **values}


def test_thresholds_list_create_and_conflict(
    db_client: TestClient, headers: Headers, other_headers: Headers
) -> None:
    assert db_client.get("/v1/athlete/thresholds", headers=headers).json() == []

    created = db_client.post(
        "/v1/athlete/thresholds",
        headers=headers,
        json=_threshold("2026-09-01", ftp_w=220, weight_kg=58.25, threshold_pace_s_per_km=290.5),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["ftp_w"] == 220
    assert body["weight_kg"] == 58.25
    assert body["threshold_pace_s_per_km"] == 290.5
    assert body["source"] == "manual"
    assert body["cycling_lthr_bpm"] is None
    assert body["running_lthr_bpm"] is None
    assert body["legacy_lthr_bpm"] is None

    db_client.post(
        "/v1/athlete/thresholds", headers=headers, json=_threshold("2026-11-01", ftp_w=230)
    )
    db_client.post(
        "/v1/athlete/thresholds", headers=headers, json=_threshold("2026-10-01", ftp_w=225)
    )

    listed = db_client.get("/v1/athlete/thresholds", headers=headers).json()
    assert [row["effective_from"] for row in listed] == ["2026-11-01", "2026-10-01", "2026-09-01"]

    duplicate = db_client.post(
        "/v1/athlete/thresholds", headers=headers, json=_threshold("2026-10-01", ftp_w=240)
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"

    # Otro atleta no ve los umbrales y puede usar la misma fecha.
    assert db_client.get("/v1/athlete/thresholds", headers=other_headers).json() == []
    same_date = db_client.post(
        "/v1/athlete/thresholds", headers=other_headers, json=_threshold("2026-10-01", ftp_w=300)
    )
    assert same_date.status_code == 201


def test_current_threshold_picks_latest_row_on_date(
    db_client: TestClient, headers: Headers
) -> None:
    no_rows = db_client.get("/v1/athlete/thresholds/current", headers=headers)
    assert no_rows.status_code == 404
    assert no_rows.json()["error"]["code"] == "not_found"

    db_client.post(
        "/v1/athlete/thresholds", headers=headers, json=_threshold("2026-09-01", ftp_w=220)
    )
    db_client.post(
        "/v1/athlete/thresholds",
        headers=headers,
        json=_threshold(
            "2026-10-01", cycling_lthr_bpm=170, running_lthr_bpm=177, threshold_pace_s_per_km=292
        ),
    )

    before = db_client.get("/v1/athlete/thresholds/current?on=2026-08-31", headers=headers)
    assert before.status_code == 404

    september = db_client.get("/v1/athlete/thresholds/current?on=2026-09-30", headers=headers)
    assert september.status_code == 200
    body = september.json()
    assert body["on"] == "2026-09-30"
    assert body["threshold"]["ftp_w"] == 220
    assert body["zones"]["hr_cycling"] is None
    assert body["zones"]["hr_running"] is None
    assert body["zones"]["running_pace"] is None
    assert body["zones"]["trail_hr"] is None
    assert [zone["low"] for zone in body["zones"]["power"]] == [z.low for z in power_zones(220)]

    # Fila completa, sin combinar con la anterior: el FTP de septiembre no se arrastra.
    october = db_client.get("/v1/athlete/thresholds/current?on=2026-10-01", headers=headers).json()
    assert october["threshold"]["ftp_w"] is None
    assert october["zones"]["power"] is None
    assert [z["high"] for z in october["zones"]["hr_cycling"]] == [
        z.high for z in hr_zones(170, HrZoneSport.CYCLING)
    ]
    assert [z["low"] for z in october["zones"]["hr_running"]] == [
        z.low for z in hr_zones(177, HrZoneSport.RUNNING)
    ]
    assert [(z["code"], z["low"], z["high"]) for z in october["zones"]["trail_hr"]] == [
        (z.code, z.low, z.high) for z in trail_hr_zones(177)
    ]
    assert [(z["low"], z["high"]) for z in october["zones"]["running_pace"]] == [
        (z.low, z.high) for z in pace_zones(292)
    ]


def test_threshold_rejects_old_lthr_field_and_lthr_above_hr_max(
    db_client: TestClient, headers: Headers
) -> None:
    old = db_client.post(
        "/v1/athlete/thresholds", headers=headers, json=_threshold("2026-10-01", lthr_bpm=170)
    )
    assert old.status_code == 422
    readonly = db_client.post(
        "/v1/athlete/thresholds",
        headers=headers,
        json=_threshold("2026-10-01", legacy_lthr_bpm=170),
    )
    assert readonly.status_code == 422
    for field in ("cycling_lthr_bpm", "running_lthr_bpm"):
        too_high = db_client.post(
            "/v1/athlete/thresholds",
            headers=headers,
            json=_threshold("2026-10-01", hr_max_bpm=180, **{field: 181}),
        )
        assert too_high.status_code == 422


def test_current_threshold_defaults_to_today_in_athlete_timezone(
    db_client: TestClient, headers: Headers
) -> None:
    # UTC+14: "hoy" allí suele ser mañana en UTC.
    db_client.patch("/v1/athlete/profile", headers=headers, json={"timezone": "Pacific/Kiritimati"})
    today = datetime.now(ZoneInfo("Pacific/Kiritimati")).date()
    db_client.post(
        "/v1/athlete/thresholds", headers=headers, json=_threshold(today.isoformat(), ftp_w=200)
    )

    response = db_client.get("/v1/athlete/thresholds/current", headers=headers)

    assert response.status_code == 200
    assert response.json()["on"] == today.isoformat()


def test_current_threshold_is_isolated(
    db_client: TestClient, headers: Headers, other_headers: Headers
) -> None:
    db_client.post(
        "/v1/athlete/thresholds", headers=headers, json=_threshold("2026-01-01", ftp_w=200)
    )

    response = db_client.get("/v1/athlete/thresholds/current", headers=other_headers)

    assert response.status_code == 404


# --- Disponibilidad --------------------------------------------------------------------------


def test_availability_defaults_and_replace(
    db_client: TestClient,
    headers: Headers,
    other_headers: Headers,
    user_id: uuid.UUID,
    engine: Engine,
) -> None:
    default = db_client.get("/v1/athlete/availability", headers=headers)
    assert default.status_code == 200
    assert default.json() == {
        "days": [
            {
                "weekday": weekday,
                "max_minutes": None,
                "sports": [],
                "preferred_time": "any",
                "is_preferred_rest": False,
            }
            for weekday in range(7)
        ]
    }

    week = WeekAvailability.model_json_schema()["examples"][0]
    shuffled = {"days": list(reversed(week["days"]))}
    replaced = db_client.put("/v1/athlete/availability", headers=headers, json=shuffled)
    assert replaced.status_code == 200, replaced.text
    assert replaced.json() == week
    assert db_client.get("/v1/athlete/availability", headers=headers).json() == week

    second = {"days": [{"weekday": weekday, "max_minutes": 30} for weekday in range(7)]}
    again = db_client.put("/v1/athlete/availability", headers=headers, json=second).json()
    assert [day["max_minutes"] for day in again["days"]] == [30] * 7
    assert [day["sports"] for day in again["days"]] == [[]] * 7
    assert _count(engine, AvailabilitySlot, user_id) == 7

    assert db_client.get("/v1/athlete/availability", headers=other_headers).json() == default.json()


# --- Calendario ------------------------------------------------------------------------------

RACE = {
    "discipline": "trail_running",
    "distance_m": 42000.0,
    "ascent_m": 2400.0,
    "priority": "A",
    "goal": "Terminar por debajo de 6 h.",
    "source_url": "https://example.com/carrera",
}


def _event(**values: Any) -> dict[str, Any]:
    return {"kind": "social", "title": "Cena", "start_at": "2026-12-05T20:00:00+01:00", **values}


def _create(client: TestClient, headers: Headers, **values: Any) -> dict[str, Any]:
    response = client.post("/v1/calendar/events", headers=headers, json=_event(**values))
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _list(client: TestClient, headers: Headers, from_: str, to: str) -> list[str]:
    response = client.get(f"/v1/calendar/events?from={from_}&to={to}", headers=headers)
    assert response.status_code == 200, response.text
    return [event["title"] for event in response.json()]


def test_create_event_without_and_with_race(db_client: TestClient, headers: Headers) -> None:
    social = _create(db_client, headers, details={"place": "Casa"}, notes="Llevar postre")
    assert social["race"] is None
    assert social["details"] == {"place": "Casa"}
    assert social["all_day"] is True
    assert social["training_impact"] == "none"
    assert datetime.fromisoformat(social["start_at"]) == datetime.fromisoformat(
        "2026-12-05T20:00:00+01:00"
    )

    default_race = _create(db_client, headers, kind="race", title="Carrera B")
    assert default_race["race"] == {
        "discipline": None,
        "distance_m": None,
        "ascent_m": None,
        "priority": "B",
        "goal": None,
        "enrichment_status": "none",
        "source_url": None,
    }

    race = _create(db_client, headers, kind="race", title="Trail", race=RACE)
    assert race["race"] == {**RACE, "enrichment_status": "none"}


def test_list_events_by_overlap_in_athlete_timezone(
    db_client: TestClient, headers: Headers, other_headers: Headers
) -> None:
    # Perfil en Europe/Madrid (UTC+1 en diciembre).
    _create(db_client, headers, title="Antes", start_at="2026-11-30T10:00:00Z")
    # 30-nov 23:30 UTC = 1-dic 00:30 en Madrid.
    _create(db_client, headers, title="Medianoche", start_at="2026-11-30T23:30:00Z")
    _create(
        db_client,
        headers,
        kind="travel",
        title="Viaje",
        start_at="2026-11-28T00:00:00+01:00",
        end_at="2026-12-03T23:59:00+01:00",
    )
    _create(db_client, headers, title="Dentro", start_at="2026-12-02T18:00:00+01:00")
    # 3-dic 23:30 UTC = 4-dic 00:30 en Madrid: fuera del rango.
    _create(db_client, headers, title="Después", start_at="2026-12-03T23:30:00Z")
    _create(db_client, other_headers, title="Otro atleta", start_at="2026-12-02T10:00:00Z")

    assert _list(db_client, headers, "2026-12-01", "2026-12-03") == [
        "Viaje",
        "Medianoche",
        "Dentro",
    ]
    assert _list(db_client, headers, "2026-11-30", "2026-11-30") == ["Viaje", "Antes"]
    assert _list(db_client, headers, "2027-01-01", "2027-01-31") == []
    assert _list(db_client, other_headers, "2026-12-01", "2026-12-03") == ["Otro atleta"]

    # Con otra zona horaria cambian los límites del día.
    db_client.patch("/v1/athlete/profile", headers=headers, json={"timezone": "UTC"})
    assert _list(db_client, headers, "2026-11-30", "2026-11-30") == ["Viaje", "Antes", "Medianoche"]


def test_list_events_includes_race_data(db_client: TestClient, headers: Headers) -> None:
    _create(db_client, headers, kind="race", title="Trail", race=RACE)
    _create(db_client, headers, title="Cena")

    events = db_client.get(
        "/v1/calendar/events?from=2026-12-01&to=2026-12-31", headers=headers
    ).json()

    assert {event["title"]: event["race"] is not None for event in events} == {
        "Trail": True,
        "Cena": False,
    }
    assert next(e for e in events if e["title"] == "Trail")["race"]["priority"] == "A"


def test_patch_event_fields_and_race_merge(db_client: TestClient, headers: Headers) -> None:
    event = _create(
        db_client,
        headers,
        kind="race",
        title="Trail",
        end_at="2026-12-05T23:00:00+01:00",
        notes="nota",
        race=RACE,
    )
    url = f"/v1/calendar/events/{event['id']}"

    response = db_client.patch(
        url,
        headers=headers,
        json={
            "title": "Trail (42K)",
            "end_at": None,
            "notes": None,
            "details": {"bib": 12},
            "race": {"priority": "C", "goal": None, "enrichment_status": "confirmed"},
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Trail (42K)"
    assert body["end_at"] is None
    assert body["notes"] is None
    assert body["details"] == {"bib": 12}
    assert body["kind"] == "race"
    assert body["race"] == {
        **RACE,
        "priority": "C",
        "goal": None,
        "enrichment_status": "confirmed",
    }
    assert body["updated_at"] >= event["updated_at"]


def test_patch_event_kind_changes_manage_race(
    db_client: TestClient, headers: Headers, user_id: uuid.UUID, engine: Engine
) -> None:
    event = _create(db_client, headers, kind="race", title="Trail", race=RACE)
    url = f"/v1/calendar/events/{event['id']}"

    to_travel = db_client.patch(url, headers=headers, json={"kind": "travel"})
    assert to_travel.status_code == 200
    assert to_travel.json()["race"] is None
    assert _count(engine, Race, user_id) == 0

    back_to_race = db_client.patch(
        url, headers=headers, json={"kind": "race", "race": {"distance_m": 21000}}
    )
    assert back_to_race.status_code == 200
    race = back_to_race.json()["race"]
    assert race["priority"] == "B"  # los datos anteriores se borraron
    assert race["distance_m"] == 21000
    assert race["discipline"] is None

    social = _create(db_client, headers, title="Cena")
    to_race = db_client.patch(
        f"/v1/calendar/events/{social['id']}", headers=headers, json={"kind": "race"}
    )
    assert to_race.json()["race"]["priority"] == "B"


def test_patch_event_conflicts(db_client: TestClient, headers: Headers) -> None:
    event = _create(db_client, headers, end_at="2026-12-05T22:00:00+01:00")
    url = f"/v1/calendar/events/{event['id']}"

    end_before_start = db_client.patch(
        url, headers=headers, json={"start_at": "2026-12-06T10:00:00+01:00"}
    )
    assert end_before_start.status_code == 409
    assert end_before_start.json()["error"]["code"] == "conflict"

    race_on_social = db_client.patch(url, headers=headers, json={"race": {"priority": "A"}})
    assert race_on_social.status_code == 409

    # Nada ha cambiado.
    unchanged = db_client.get(
        "/v1/calendar/events?from=2026-12-05&to=2026-12-05", headers=headers
    ).json()
    assert unchanged == [event]


def test_patch_and_delete_are_isolated_and_404(
    db_client: TestClient, headers: Headers, other_headers: Headers
) -> None:
    event = _create(db_client, headers, kind="race", title="Trail", race=RACE)
    url = f"/v1/calendar/events/{event['id']}"
    missing = f"/v1/calendar/events/{uuid.uuid4()}"

    for target, who in ((url, other_headers), (missing, headers)):
        patched = db_client.patch(target, headers=who, json={"title": "Hackeado"})
        assert patched.status_code == 404
        assert patched.json()["error"]["code"] == "not_found"
        assert db_client.delete(target, headers=who).status_code == 404

    assert _list(db_client, headers, "2026-12-05", "2026-12-05") == ["Trail"]


def test_delete_event_removes_race(
    db_client: TestClient, headers: Headers, user_id: uuid.UUID, engine: Engine
) -> None:
    event = _create(db_client, headers, kind="race", title="Trail", race=RACE)
    url = f"/v1/calendar/events/{event['id']}"

    deleted = db_client.delete(url, headers=headers)

    assert deleted.status_code == 204
    assert deleted.content == b""
    assert _count(engine, Race, user_id) == 0
    assert _list(db_client, headers, "2026-12-05", "2026-12-05") == []
    assert db_client.delete(url, headers=headers).status_code == 404


def test_threshold_rows_belong_to_jwt_user(
    db_client: TestClient, headers: Headers, user_id: uuid.UUID, engine: Engine
) -> None:
    db_client.post(
        "/v1/athlete/thresholds", headers=headers, json=_threshold("2026-01-01", ftp_w=200)
    )

    assert _count(engine, AthleteThreshold, user_id) == 1
