"""Entrenos planificados y fuerza (#30): leer el plan, la sesión, registrar series y completar.

Todo se filtra por el atleta del JWT: un entreno de otro atleta responde 404. La generación de
sesiones por el coach llega en Fuerza 5; aquí sólo la estructura y el registro.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import error_responses
from app.schemas.strength import (
    SEARCH_LIMIT_MAX,
    ExerciseLastLogOut,
    ExerciseOut,
    LastSetOut,
    PlannedStrengthExerciseOut,
    PlannedWorkoutOut,
    PlannedWorkoutRange,
    StrengthActivityOut,
    StrengthSetLogOut,
    StrengthSetsPut,
    StrengthWorkoutComplete,
    StrengthWorkoutOut,
)
from app.services import strength
from app.services.strength import StrengthWorkoutDetail

planned_router = APIRouter(prefix="/planned-workouts", tags=["planned-workouts"])
router = APIRouter(prefix="/strength", tags=["strength"])


def _workout_out(detail: StrengthWorkoutDetail) -> StrengthWorkoutOut:
    base = PlannedWorkoutOut.model_validate(detail.workout)
    return StrengthWorkoutOut(
        **base.model_dump(),
        exercises=[
            PlannedStrengthExerciseOut.model_validate(
                {
                    **{
                        name: getattr(planned, name)
                        for name in PlannedStrengthExerciseOut.model_fields
                        if name != "exercise"
                    },
                    "exercise": ExerciseOut.model_validate(exercise),
                }
            )
            for planned, exercise in detail.exercises
        ],
        set_logs=[StrengthSetLogOut.model_validate(log) for log in detail.set_logs],
        activity=None
        if detail.activity is None
        else StrengthActivityOut.model_validate(detail.activity),
    )


@planned_router.get("", responses=error_responses())
def list_planned_workouts(
    user: CurrentUser, db: DbSession, date_range: Annotated[PlannedWorkoutRange, Query()]
) -> list[PlannedWorkoutOut]:
    """Entrenos planificados de cualquier disciplina con fecha en `[from, to]`, por fecha.

    Sin paginar: el rango máximo es de 366 días. El detalle de una sesión de fuerza está en
    `GET /v1/strength/workouts/{id}`.
    """
    return [
        PlannedWorkoutOut.model_validate(workout)
        for workout in strength.list_planned_workouts(db, user.id, date_range.from_, date_range.to)
    ]


@router.get("/exercises", responses=error_responses())
def search_exercises(
    user: CurrentUser,
    db: DbSession,
    q: Annotated[
        str | None,
        Query(
            max_length=120,
            description="Texto en el nombre o un alias, sin distinguir mayúsculas ni acentos.",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=SEARCH_LIMIT_MAX)] = 50,
) -> list[ExerciseOut]:
    """Catálogo de ejercicios (los del sistema y los propios).

    Con `q`, primero los que empiezan por la búsqueda y después el resto, por nombre.
    """
    return [
        ExerciseOut.model_validate(exercise)
        for exercise in strength.search_exercises(db, user.id, q, limit)
    ]


@router.get("/exercises/{exercise_id}/last-log", responses=error_responses(404))
def exercise_last_log(user: CurrentUser, db: DbSession, exercise_id: UUID) -> ExerciseLastLogOut:
    """Series del ejercicio (peso y repeticiones o segundos) en la última sesión completada.

    Si nunca se ha registrado, `performed_on` es null y `sets` está vacía. 404 si el ejercicio no
    existe.
    """
    last = strength.last_log(db, user.id, exercise_id)
    return ExerciseLastLogOut(
        exercise=ExerciseOut.model_validate(last.exercise),
        performed_on=last.performed_on,
        activity_id=last.activity_id,
        planned_workout_id=last.planned_workout_id,
        sets=[LastSetOut.model_validate(log) for log in last.sets],
    )


@router.get("/workouts/{workout_id}", responses=error_responses(404, 422))
def get_strength_workout(user: CurrentUser, db: DbSession, workout_id: UUID) -> StrengthWorkoutOut:
    """Sesión de fuerza: ejercicios planificados, series hechas y, si está completada, su
    actividad. 422 `not_strength` si el entreno es de otra disciplina."""
    return _workout_out(strength.get_strength_workout(db, user.id, workout_id))


@router.put("/workouts/{workout_id}/sets", responses=error_responses(404, 409, 422))
def replace_sets(
    user: CurrentUser, db: DbSession, workout_id: UUID, body: StrengthSetsPut
) -> StrengthWorkoutOut:
    """Registra o edita las series: la lista sustituye a todas las registradas antes.

    Se puede usar durante el entreno (enviando la lista acumulada) y después de completarlo.
    409 si el entreno está saltado. 422 con `code`: `not_strength`,
    `unknown_planned_exercise`, `unknown_exercise`, `mode_mismatch` y `duplicate_set`.
    """
    return _workout_out(strength.replace_sets(db, user.id, workout_id, body.sets))


@router.post("/workouts/{workout_id}/complete", responses=error_responses(404, 409, 422))
def complete_workout(
    user: CurrentUser, db: DbSession, workout_id: UUID, body: StrengthWorkoutComplete
) -> StrengthWorkoutOut:
    """Completa la sesión: crea la actividad de fuerza y marca el entreno como hecho.

    La actividad lleva `sport = strength`, `source = manual`, la duración y el `rpe`; su carga
    es `session_rpe` (minutos × RPE), que no suma en CTL/ATL/TSB. Las series registradas pasan
    a la actividad. 409 si el entreno ya está hecho o saltado; 422 `not_strength`.
    """
    return _workout_out(
        strength.complete_workout(
            db,
            user.id,
            workout_id,
            started_at=body.started_at,
            duration_s=body.duration_s,
            rpe=body.rpe,
        )
    )
