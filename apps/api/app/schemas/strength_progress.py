"""Schemas del rendimiento de fuerza (#33): resumen semanal y progresión por ejercicio.

Todo lo calcula la API (`app/services/strength_progress.py`). La carga de fuerza es
`session_rpe` (minutos × RPE) y nunca se suma a la carga de resistencia ni a CTL/ATL/TSB.
"""

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.strength import _EXERCISE_EXAMPLE, ExerciseOut

_ACTIVITY_IDS = (
    "1f0e2d3c-4b5a-4968-8776-655443322110",
    "2e1d3c4b-5a69-4877-8665-544332211009",
    "3d2c4b5a-6978-4866-9554-433221100998",
)
_WORKOUT_IDS = (
    "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
    None,
)


# --- Resumen semanal -------------------------------------------------------------------------


class StrengthWeekOut(BaseModel):
    """Una semana (de lunes a domingo, días locales del atleta).

    - `sessions`: actividades de fuerza de la semana (sin duplicados).
    - `duration_s`: suma de su duración.
    - `load`: suma de su carga `session_rpe` (minutos × RPE, Foster), redondeada a 1 decimal.
      Es la carga de fuerza: **no** es TSS y no suma en CTL/ATL/TSB.
    - `sessions_without_load`: sesiones sin RPE, que cuentan en `sessions` y `duration_s`
      pero no en `load`.
    """

    week_start: date = Field(description="Lunes de la semana.")
    sessions: int = Field(ge=0)
    duration_s: int = Field(ge=0)
    load: float = Field(ge=0)
    sessions_without_load: int = Field(ge=0)


def _weekly_example() -> dict[str, Any]:
    return {
        "from": "2026-10-26",
        "to": "2026-11-19",
        "weeks": [
            {
                "week_start": "2026-10-26",
                "sessions": 1,
                "duration_s": 2700,
                "load": 270.0,
                "sessions_without_load": 0,
            },
            {
                "week_start": "2026-11-02",
                "sessions": 2,
                "duration_s": 5400,
                "load": 495.0,
                "sessions_without_load": 0,
            },
            {
                "week_start": "2026-11-09",
                "sessions": 0,
                "duration_s": 0,
                "load": 0.0,
                "sessions_without_load": 0,
            },
            {
                "week_start": "2026-11-16",
                "sessions": 2,
                "duration_s": 5100,
                "load": 330.0,
                "sessions_without_load": 1,
            },
        ],
    }


class StrengthWeeklyOut(BaseModel):
    """Una semana por cada lunes desde la semana de `from` hasta la de `to`, por fecha.

    Las semanas sin fuerza aparecen con todo a 0. La última semana es la que contiene `to`
    (con `to` = hoy, la semana en curso).
    """

    model_config = ConfigDict(
        populate_by_name=True, json_schema_extra={"examples": [_weekly_example()]}
    )

    from_: date = Field(alias="from")
    to: date
    weeks: list[StrengthWeekOut]


# --- Progresión por ejercicio ----------------------------------------------------------------


class PerformedExerciseOut(BaseModel):
    """Un ejercicio con series hechas en sesiones completadas.

    `last_max_weight_kg` es el peso máximo de la última sesión (null si no se usó peso).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "exercise": _EXERCISE_EXAMPLE,
                    "sessions": 3,
                    "first_performed_on": "2026-10-29",
                    "last_performed_on": "2026-11-17",
                    "last_max_weight_kg": 62.5,
                }
            ]
        }
    )

    exercise: ExerciseOut
    sessions: int = Field(ge=1, description="Sesiones completadas con el ejercicio.")
    first_performed_on: date
    last_performed_on: date
    last_max_weight_kg: float | None


class ExerciseSessionOut(BaseModel):
    """Lo hecho con un ejercicio en una sesión completada. Sólo cuentan las series hechas.

    - `max_weight_kg`: peso máximo de sus series (null si ninguna tiene peso).
    - `volume_kg`: suma de repeticiones × peso de cada serie (con series iguales, series ×
      repeticiones × peso). Null si ninguna serie tiene peso y repeticiones.
    - `best_set_reps`: repeticiones de la mejor serie, la de más peso (a igual peso, la de más
      repeticiones; sin peso, la de más repeticiones). Null en ejercicios por segundos.
    - `best_set_seconds`: igual, en los ejercicios por segundos.
    """

    performed_on: date = Field(description="Día local de la sesión.")
    activity_id: UUID
    planned_workout_id: UUID | None
    sets: int = Field(ge=1, description="Series hechas.")
    total_reps: int | None = Field(description="Repeticiones de todas las series.")
    total_seconds: int | None = Field(description="Segundos de todas las series.")
    max_weight_kg: float | None
    volume_kg: float | None
    best_set_reps: int | None
    best_set_seconds: int | None


def _session_example(
    index: int, day: str, weights: tuple[float, ...], reps: int = 8
) -> dict[str, Any]:
    return {
        "performed_on": day,
        "activity_id": _ACTIVITY_IDS[index],
        "planned_workout_id": _WORKOUT_IDS[index],
        "sets": len(weights),
        "total_reps": reps * len(weights),
        "total_seconds": None,
        "max_weight_kg": max(weights),
        "volume_kg": round(sum(w * reps for w in weights), 1),
        "best_set_reps": reps,
        "best_set_seconds": None,
    }


class ExerciseProgressOut(BaseModel):
    """Historial de un ejercicio: una entrada por sesión completada, de la más antigua a la
    más reciente. Vacío si nunca se ha hecho."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "exercise": _EXERCISE_EXAMPLE,
                    "sessions": [
                        _session_example(0, "2026-10-29", (55.0, 57.5, 57.5)),
                        _session_example(1, "2026-11-05", (57.5, 60.0, 60.0)),
                        _session_example(2, "2026-11-17", (60.0, 62.5, 62.5)),
                    ],
                }
            ]
        }
    )

    exercise: ExerciseOut
    sessions: list[ExerciseSessionOut]
