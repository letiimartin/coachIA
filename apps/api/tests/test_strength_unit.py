"""Fuerza (#30) sin BD: búsqueda normalizada, catálogo de la migración, schemas y contrato."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.text import search_key, search_text
from app.models import ExerciseMode, MuscleGroup
from app.schemas.strength import (
    PlannedWorkoutRange,
    StrengthSetIn,
    StrengthSetsPut,
    StrengthWorkoutComplete,
)

MIGRATION = next(Path("alembic/versions").glob("*_e4b8468591c1_*.py"))
WORKOUT = "4c2b1a09-8f7e-4d6c-9b5a-3e2d1c0b9a8f"
EXERCISE = "0b7c3f9e-1d2a-4e5b-8c6d-7e8f9a0b1c2d"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("strength_migration", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- Búsqueda ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["Peso muerto rumano", "PESO-MUERTO rumáno", "  peso   muerto\trumano ", "Pesó Muerto Rumano"],
)
def test_search_key_ignores_case_accents_and_signs(text: str) -> None:
    assert search_key(text) == "peso muerto rumano"


def test_search_key_maps_enye_and_keeps_digits() -> None:
    assert search_key("Ñandú 90/90") == "nandu 90 90"


def test_search_text_joins_name_and_aliases() -> None:
    assert search_text("Step-up", ["Subida al cajón", "", "!!"]) == "step up|subida al cajon"


# --- Catálogo inicial (datos de la migración) -------------------------------------------------


def test_catalog_has_about_fifty_unique_exercises() -> None:
    catalog = _migration().CATALOG
    slugs = [row[0] for row in catalog]
    names = [search_key(row[1]) for row in catalog]

    assert 45 <= len(catalog) <= 65
    assert len(set(slugs)) == len(slugs)
    assert len(set(names)) == len(names)


def test_catalog_values_are_valid() -> None:
    for slug, name, aliases, muscle_group, mode in _migration().CATALOG:
        assert slug.replace("_", "").isalnum() and slug == slug.lower(), slug
        assert 0 < len(name) <= 120
        assert all(0 < len(alias) <= 120 for alias in aliases)
        MuscleGroup(muscle_group)
        ExerciseMode(mode)


def test_catalog_aliases_do_not_collide_between_exercises() -> None:
    owner: dict[str, str] = {}
    for slug, name, aliases, *_ in _migration().CATALOG:
        for key in (search_key(name), *(search_key(alias) for alias in aliases)):
            assert owner.setdefault(key, slug) == slug, f"«{key}» en {owner[key]} y {slug}"


def test_migration_search_text_matches_the_app() -> None:
    migration = _migration()
    for _, name, aliases, *_ in migration.CATALOG:
        assert migration._search_text(name, aliases) == search_text(name, list(aliases))


def test_catalog_covers_the_approved_families() -> None:
    slugs = {row[0] for row in _migration().CATALOG}
    approved = {
        "back_squat",
        "deadlift",
        "forward_lunge",
        "step_up",
        "hip_thrust",
        "glute_bridge",
        "standing_calf_raise",
        "overhead_press",
        "barbell_row",
        "pull_up",
        "plank",
        "box_jump",
    }
    assert approved <= slugs


# --- Schemas ----------------------------------------------------------------------------------


def _set(**values: Any) -> dict[str, Any]:
    return {"exercise_id": EXERCISE, "set_number": 1, "reps": 8, **values}


def test_set_needs_an_exercise() -> None:
    with pytest.raises(ValidationError, match="planned_exercise_id"):
        StrengthSetIn.model_validate({"set_number": 1, "reps": 8})


@pytest.mark.parametrize(
    "values", [{"reps": None}, {"seconds": 30}], ids=["sin_cantidad", "reps_y_segundos"]
)
def test_set_needs_exactly_one_of_reps_and_seconds(values: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="exactamente uno"):
        StrengthSetIn.model_validate(_set(**values))


@pytest.mark.parametrize(
    "values",
    [
        {"set_number": 0},
        {"reps": -1},
        {"weight_kg": -5},
        {"rpe": 11},
        {"rir": -1},
        {"unknown": 1},
    ],
)
def test_set_rejects_out_of_range_values(values: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        StrengthSetIn.model_validate(_set(**values))


def test_set_defaults_to_completed() -> None:
    parsed = StrengthSetIn.model_validate(_set(weight_kg=62.5, rir=2))
    assert parsed.completed is True
    assert parsed.weight_kg == 62.5


def test_sets_put_has_a_limit() -> None:
    with pytest.raises(ValidationError):
        StrengthSetsPut.model_validate({"sets": [_set(set_number=1)] * 201})


@pytest.mark.parametrize(
    "values",
    [
        {"started_at": "2026-11-19T18:30:00"},
        {"duration_s": 0},
        {"rpe": 0},
        {"rpe": None},
    ],
    ids=["sin_zona_horaria", "duracion_cero", "rpe_cero", "sin_rpe"],
)
def test_complete_validation(values: dict[str, Any]) -> None:
    body = {"started_at": "2026-11-19T18:30:00+01:00", "duration_s": 3000, "rpe": 7, **values}
    with pytest.raises(ValidationError):
        StrengthWorkoutComplete.model_validate(body)


def test_range_validation() -> None:
    with pytest.raises(ValidationError, match="anterior"):
        PlannedWorkoutRange.model_validate({"from": "2026-11-10", "to": "2026-11-01"})
    with pytest.raises(ValidationError, match="366"):
        PlannedWorkoutRange.model_validate({"from": "2026-01-01", "to": "2027-01-02"})


# --- Contrato ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/v1/planned-workouts?from=2026-11-01&to=2026-11-30"),
        ("get", "/v1/strength/exercises"),
        ("get", f"/v1/strength/exercises/{EXERCISE}/last-log"),
        ("get", f"/v1/strength/workouts/{WORKOUT}"),
        ("put", f"/v1/strength/workouts/{WORKOUT}/sets"),
        ("post", f"/v1/strength/workouts/{WORKOUT}/complete"),
    ],
)
def test_endpoints_require_jwt(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_contract_documents_the_strength_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert set(paths["/v1/planned-workouts"]) == {"get"}
    assert set(paths["/v1/strength/exercises"]) == {"get"}
    assert set(paths["/v1/strength/exercises/{exercise_id}/last-log"]) == {"get"}
    assert set(paths["/v1/strength/workouts/{workout_id}"]) == {"get"}
    assert set(paths["/v1/strength/workouts/{workout_id}/sets"]) == {"put"}
    assert set(paths["/v1/strength/workouts/{workout_id}/complete"]) == {"post"}
