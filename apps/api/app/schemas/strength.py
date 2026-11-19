"""Schemas de los entrenos planificados y de la fuerza (#30).

Los rangos replican las restricciones de `app/models/plan.py` y `app/models/strength.py`.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.activity import LoadMethod
from app.models.common import Sport
from app.models.plan import PlannedWorkoutStatus
from app.models.strength import ExerciseMode, ExerciseOrigin, MuscleGroup

MAX_RANGE_DAYS = 366
MAX_SETS_PER_SESSION = 200
SEARCH_LIMIT_MAX = 100

WeightKg = Annotated[float, Field(ge=0, lt=1000, description="Peso en kg (2 decimales).")]
Rpe = Annotated[int, Field(ge=1, le=10, description="Esfuerzo percibido (1-10).")]
Rir = Annotated[int, Field(ge=0, le=10, description="Repeticiones en reserva (0-10).")]

_EXERCISE_EXAMPLE: dict[str, Any] = {
    "id": "0b7c3f9e-1d2a-4e5b-8c6d-7e8f9a0b1c2d",
    "slug": "back_squat",
    "name": "Sentadilla trasera",
    "aliases": ["Sentadilla con barra", "Back squat"],
    "muscle_group": "quadriceps",
    "mode": "reps",
    "origin": "system",
}
_WORKOUT_ID = "4c2b1a09-8f7e-4d6c-9b5a-3e2d1c0b9a8f"
_PLANNED_EXERCISE_ID = "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d"
_ACTIVITY_ID = "7a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d"


# --- Catálogo --------------------------------------------------------------------------------


class ExerciseOut(BaseModel):
    """Ejercicio del catálogo. `id` es el identificador estable; `slug`, su forma legible."""

    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"examples": [_EXERCISE_EXAMPLE]}
    )

    id: UUID
    slug: str
    name: str
    aliases: list[str]
    muscle_group: MuscleGroup
    mode: ExerciseMode = Field(
        description="`reps`: cada serie se mide en repeticiones; `seconds`, en segundos."
    )
    origin: ExerciseOrigin = Field(
        description="`system` (catálogo común), `coach` o `user` (propios de la atleta)."
    )


class LastSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    set_number: int
    reps: int | None
    seconds: int | None
    weight_kg: float | None
    rpe: int | None
    rir: int | None
    completed: bool


class ExerciseLastLogOut(BaseModel):
    """Última sesión **completada** en la que se registró el ejercicio, con sus series.

    Si nunca se ha registrado, `performed_on`, `activity_id` y `planned_workout_id` son null
    y `sets` está vacía.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "exercise": _EXERCISE_EXAMPLE,
                    "performed_on": "2026-11-12",
                    "activity_id": _ACTIVITY_ID,
                    "planned_workout_id": _WORKOUT_ID,
                    "sets": [
                        {
                            "set_number": 1,
                            "reps": 8,
                            "seconds": None,
                            "weight_kg": 60.0,
                            "rpe": None,
                            "rir": 2,
                            "completed": True,
                        }
                    ],
                }
            ]
        }
    )

    exercise: ExerciseOut
    performed_on: date | None = Field(description="Día local de la sesión.")
    activity_id: UUID | None
    planned_workout_id: UUID | None
    sets: list[LastSetOut] = Field(description="Series de ese ejercicio, por `set_number`.")


# --- Entrenos planificados -------------------------------------------------------------------


class PlannedWorkoutRange(BaseModel):
    """Rango de fechas (ambas incluidas, días locales del atleta). Máximo 366 días."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: date = Field(alias="from", description="Primer día del rango (incluido).")
    to: date = Field(description="Último día del rango (incluido).")

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        if self.to < self.from_:
            raise ValueError("'to' no puede ser anterior a 'from'")
        if self.to - self.from_ >= timedelta(days=MAX_RANGE_DAYS):
            raise ValueError(f"el rango no puede superar {MAX_RANGE_DAYS} días")
        return self


_WORKOUT_EXAMPLE: dict[str, Any] = {
    "id": _WORKOUT_ID,
    "sport": "strength",
    "scheduled_on": "2026-11-19",
    "title": "Fuerza de piernas",
    "status": "planned",
    "coach_reason": "Semana de base: fuerza máxima con poco volumen para no afectar al rodaje.",
    "exercise_count": 1,
    "planned_duration_s": 3000,
    "activity_id": None,
    "created_at": "2026-11-18T10:00:00Z",
    "updated_at": "2026-11-18T10:00:00Z",
}


class PlannedWorkoutOut(BaseModel):
    """Entreno planificado de cualquier disciplina. La fuerza es el primer tipo.

    - `planned`: pendiente.
    - `done`: hecho; `activity_id` es la actividad que lo cumplió (null si se borró).
    - `skipped`: no se hizo.

    `exercise_count` y `planned_duration_s` resumen la sesión sin pedir su detalle. La duración
    real está en la actividad (`activity_id`) cuando el entreno está hecho.
    """

    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"examples": [_WORKOUT_EXAMPLE]}
    )

    id: UUID
    sport: Sport
    scheduled_on: date = Field(description="Día local para el que está planificado.")
    title: str
    status: PlannedWorkoutStatus
    coach_reason: str | None = Field(description="Por qué lo propone el coach.")
    exercise_count: int = Field(
        ge=0, description="Número de ejercicios planificados (0 si no es de fuerza)."
    )
    planned_duration_s: int | None = Field(
        description="Duración planificada en segundos. Null si no se ha definido (no se estima)."
    )
    activity_id: UUID | None
    created_at: datetime
    updated_at: datetime


# --- Sesión de fuerza ------------------------------------------------------------------------


class PlannedStrengthExerciseOut(BaseModel):
    """Ejercicio de la sesión. Exactamente uno de `target_reps` y `target_seconds`, según el
    `mode` del ejercicio. Peso, RPE y RIR objetivo son opcionales."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int = Field(description="Orden en la sesión (desde 1).")
    exercise: ExerciseOut
    sets: int
    target_reps: int | None
    target_seconds: int | None
    target_weight_kg: float | None
    target_rpe: int | None
    target_rir: int | None
    notes: str | None


class StrengthSetLogOut(BaseModel):
    """Serie hecha. `planned_exercise_id` es el ejercicio planificado que cumple (null si es
    una serie extra). `activity_id` es null hasta que se completa la sesión."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exercise_id: UUID
    planned_exercise_id: UUID | None
    activity_id: UUID | None
    set_number: int
    reps: int | None
    seconds: int | None
    weight_kg: float | None
    rpe: int | None
    rir: int | None
    completed: bool


class StrengthActivityOut(BaseModel):
    """Actividad creada al completar la sesión, con su carga `session_rpe` (minutos × RPE).

    Esa carga es de fuerza: no es TSS y no suma nunca en CTL/ATL/TSB. Si la sesión se completó
    sin RPE, `rpe`, `load` y `load_method` son null: no hay carga.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    start_at: datetime
    elapsed_s: int | None
    rpe: int | None
    load: float | None
    load_method: LoadMethod | None


class StrengthWorkoutOut(PlannedWorkoutOut):
    """Detalle de una sesión de fuerza: ejercicios planificados, series hechas y actividad."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    **_WORKOUT_EXAMPLE,
                    "exercises": [
                        {
                            "id": _PLANNED_EXERCISE_ID,
                            "position": 1,
                            "exercise": _EXERCISE_EXAMPLE,
                            "sets": 3,
                            "target_reps": 8,
                            "target_seconds": None,
                            "target_weight_kg": 60.0,
                            "target_rpe": None,
                            "target_rir": 2,
                            "notes": None,
                        }
                    ],
                    "set_logs": [
                        {
                            "id": "1f2e3d4c-5b6a-4978-8a7b-6c5d4e3f2a1b",
                            "exercise_id": _EXERCISE_EXAMPLE["id"],
                            "planned_exercise_id": _PLANNED_EXERCISE_ID,
                            "activity_id": None,
                            "set_number": 1,
                            "reps": 8,
                            "seconds": None,
                            "weight_kg": 60.0,
                            "rpe": None,
                            "rir": 2,
                            "completed": True,
                        }
                    ],
                    "activity": None,
                }
            ]
        }
    )

    exercises: list[PlannedStrengthExerciseOut] = Field(description="Por `position`.")
    set_logs: list[StrengthSetLogOut] = Field(
        description="Series hechas, por ejercicio planificado (las extras al final) y número."
    )
    activity: StrengthActivityOut | None = Field(description="Null hasta completar la sesión.")


class StrengthSetIn(BaseModel):
    """Una serie hecha.

    - `planned_exercise_id`: el ejercicio planificado que cumple; null para una serie extra.
    - `exercise_id`: el ejercicio hecho. Si se omite, el del ejercicio planificado. Puede ser
      otro (p. ej. una sustitución).
    - Exactamente uno de `reps` y `seconds`, según el `mode` del ejercicio.
    - `set_number` no se repite para el mismo ejercicio planificado (o el mismo ejercicio extra).
    """

    model_config = ConfigDict(extra="forbid")

    planned_exercise_id: UUID | None = None
    exercise_id: UUID | None = None
    set_number: int = Field(ge=1, le=50)
    reps: int | None = Field(default=None, ge=0, le=1000)
    seconds: int | None = Field(default=None, ge=0, le=3600)
    weight_kg: WeightKg | None = None
    rpe: Rpe | None = None
    rir: Rir | None = None
    completed: bool = True

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        if self.planned_exercise_id is None and self.exercise_id is None:
            raise ValueError("indica 'planned_exercise_id' o 'exercise_id'")
        if (self.reps is None) == (self.seconds is None):
            raise ValueError("indica exactamente uno de 'reps' y 'seconds'")
        return self


class StrengthSetsPut(BaseModel):
    """Todas las series de la sesión: sustituyen a las registradas antes.

    Sirve para registrar durante el entreno (se envía la lista acumulada) y para editar después
    de completarlo. Una lista vacía borra las series.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "sets": [
                        {
                            "planned_exercise_id": _PLANNED_EXERCISE_ID,
                            "set_number": 1,
                            "reps": 8,
                            "weight_kg": 60,
                            "rir": 2,
                        },
                        {
                            "planned_exercise_id": _PLANNED_EXERCISE_ID,
                            "set_number": 2,
                            "reps": 6,
                            "weight_kg": 60,
                            "completed": False,
                        },
                    ]
                }
            ]
        },
    )

    sets: list[StrengthSetIn] = Field(max_length=MAX_SETS_PER_SESSION)


class StrengthWorkoutComplete(BaseModel):
    """Completa la sesión: crea la actividad de fuerza (`source = manual`) con su carga
    `session_rpe` = minutos × `rpe`.

    `rpe` es opcional: sin él, la sesión queda hecha con todas sus series, pero la actividad no
    tiene RPE ni carga (no se usa un RPE por defecto ni una carga 0).
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"started_at": "2026-11-19T18:30:00+01:00", "duration_s": 3000, "rpe": 7}]
        },
    )

    started_at: AwareDatetime = Field(description="Inicio de la sesión, con zona horaria.")
    duration_s: int = Field(gt=0, le=86_400, description="Duración en segundos.")
    rpe: Rpe | None = Field(
        default=None, description="RPE de la sesión (1-10). Null u omitido: sin carga."
    )
