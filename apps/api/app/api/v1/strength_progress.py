"""Rendimiento de fuerza (#33): resumen semanal y progresión por ejercicio.

Todo se filtra por el atleta del JWT y lo calcula la API; la app sólo lo muestra. La carga de
fuerza (`session_rpe`) va aparte: nunca se suma a CTL/ATL/TSB.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import error_responses
from app.schemas.fitness import FitnessRange
from app.schemas.strength import ExerciseOut
from app.schemas.strength_progress import (
    ExerciseProgressOut,
    ExerciseSessionOut,
    PerformedExerciseOut,
    StrengthWeeklyOut,
    StrengthWeekOut,
)
from app.services import strength_progress

router = APIRouter(prefix="/strength", tags=["strength"])


@router.get("/weekly", responses=error_responses())
def strength_weekly(
    user: CurrentUser, db: DbSession, date_range: Annotated[FitnessRange, Query()]
) -> StrengthWeeklyOut:
    """Resumen semanal de fuerza: sesiones, duración y carga `session_rpe` de cada semana.

    Una semana (de lunes a domingo, días locales) por cada lunes desde la semana de `from`
    hasta la de `to` (rango máximo de 366 días), con 0 en las semanas sin fuerza. Es una
    carga distinta de la de resistencia: no suma en `GET /v1/athlete/fitness`.
    """
    weeks = strength_progress.weekly_summary(db, user.id, date_range.from_, date_range.to)
    return StrengthWeeklyOut(
        from_=date_range.from_,
        to=date_range.to,
        weeks=[
            StrengthWeekOut(
                week_start=w.week_start,
                sessions=w.sessions,
                duration_s=w.duration_s,
                load=w.load,
                sessions_without_load=w.sessions_without_load,
            )
            for w in weeks
        ],
    )


@router.get("/progress", responses=error_responses())
def performed_exercises(user: CurrentUser, db: DbSession) -> list[PerformedExerciseOut]:
    """Ejercicios hechos en sesiones completadas, del último hecho al más antiguo.

    Cada uno con su número de sesiones, la primera y la última fecha y el peso máximo de la
    última sesión. Vacía si todavía no se ha completado ninguna sesión con series.
    """
    return [
        PerformedExerciseOut(
            exercise=ExerciseOut.model_validate(item.exercise),
            sessions=item.sessions,
            first_performed_on=item.first_performed_on,
            last_performed_on=item.last_performed_on,
            last_max_weight_kg=item.last_max_weight_kg,
        )
        for item in strength_progress.performed_exercises(db, user.id)
    ]


@router.get("/exercises/{exercise_id}/progress", responses=error_responses(404))
def exercise_progress(user: CurrentUser, db: DbSession, exercise_id: UUID) -> ExerciseProgressOut:
    """Progresión de un ejercicio: una entrada por sesión completada, por fecha.

    Por sesión: series hechas, repeticiones o segundos totales, peso máximo, volumen (suma de
    repeticiones × peso) y repeticiones (o segundos) de la mejor serie. Sólo cuentan las
    series hechas (`completed`) de sesiones completadas. 404 si el ejercicio no existe.
    """
    progress = strength_progress.exercise_progress(db, user.id, exercise_id)
    return ExerciseProgressOut(
        exercise=ExerciseOut.model_validate(progress.exercise),
        sessions=[
            ExerciseSessionOut(
                performed_on=s.performed_on,
                activity_id=s.activity_id,
                planned_workout_id=s.planned_workout_id,
                sets=s.sets,
                total_reps=s.total_reps,
                total_seconds=s.total_seconds,
                max_weight_kg=s.max_weight_kg,
                volume_kg=s.volume_kg,
                best_set_reps=s.best_set_reps,
                best_set_seconds=s.best_set_seconds,
            )
            for s in progress.sessions
        ],
    )
