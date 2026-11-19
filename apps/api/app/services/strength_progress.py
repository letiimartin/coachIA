"""Rendimiento de fuerza (#33): resumen semanal y progresión por ejercicio. Sólo lectura.

- Cuenta sólo lo hecho: actividades `sport = strength` sin marcar como duplicadas y, en la
  progresión, series `completed` asignadas a una de esas actividades (una sesión en curso, con
  series sin actividad, no cuenta todavía).
- Las semanas van de lunes a domingo y los días son locales del atleta.
- La carga de fuerza es `session_rpe` (minutos × RPE). Se resume aparte y nunca se suma a la
  carga de resistencia ni a CTL/ATL/TSB (`services.fitness` la excluye de `daily_load`).
"""

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models import Activity, Exercise, LoadMethod, Sport, StrengthSetLog
from app.services.athletes import athlete_timezone
from app.services.strength import get_exercise

# --- Resumen semanal -------------------------------------------------------------------------


@dataclass(frozen=True)
class StrengthWeek:
    week_start: date
    sessions: int
    duration_s: int
    load: float
    sessions_without_load: int


def week_start(day: date) -> date:
    """Lunes de la semana de `day`."""
    return day - timedelta(days=day.weekday())


def _start_of(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz)


def weekly_summary(
    session: Session, user_id: uuid.UUID, start: date, end: date
) -> list[StrengthWeek]:
    """Una semana por cada lunes desde la semana de `start` hasta la de `end` (incluidas)."""
    tz = ZoneInfo(athlete_timezone(session, user_id))
    first = week_start(start)
    last = week_start(end)
    rows = session.execute(
        sa.select(Activity.start_at, Activity.elapsed_s, Activity.load, Activity.load_method).where(
            Activity.user_id == user_id,
            Activity.sport == Sport.STRENGTH,
            Activity.duplicate_of_id.is_(None),
            Activity.start_at >= _start_of(first, tz),
            Activity.start_at < _start_of(last + timedelta(days=7), tz),
        )
    ).all()

    sessions: dict[date, int] = {}
    duration: dict[date, int] = {}
    load: dict[date, Decimal] = {}
    without_load: dict[date, int] = {}
    for start_at, elapsed_s, activity_load, method in rows:
        week = week_start(start_at.astimezone(tz).date())
        sessions[week] = sessions.get(week, 0) + 1
        duration[week] = duration.get(week, 0) + (elapsed_s or 0)
        if activity_load is not None and method is LoadMethod.SESSION_RPE:
            load[week] = load.get(week, Decimal(0)) + activity_load
        else:
            without_load[week] = without_load.get(week, 0) + 1

    weeks: list[StrengthWeek] = []
    week = first
    while week <= last:
        weeks.append(
            StrengthWeek(
                week_start=week,
                sessions=sessions.get(week, 0),
                duration_s=duration.get(week, 0),
                load=round(float(load.get(week, Decimal(0))), 1),
                sessions_without_load=without_load.get(week, 0),
            )
        )
        week += timedelta(days=7)
    return weeks


# --- Progresión por ejercicio ----------------------------------------------------------------


@dataclass(frozen=True)
class ExerciseSession:
    performed_on: date
    activity_id: uuid.UUID
    planned_workout_id: uuid.UUID | None
    sets: int
    total_reps: int | None
    total_seconds: int | None
    max_weight_kg: float | None
    volume_kg: float | None
    best_set_reps: int | None
    best_set_seconds: int | None


@dataclass(frozen=True)
class ExerciseProgress:
    exercise: Exercise
    sessions: list[ExerciseSession]


@dataclass(frozen=True)
class PerformedExercise:
    exercise: Exercise
    sessions: int
    first_performed_on: date
    last_performed_on: date
    last_max_weight_kg: float | None


def _float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _best_set(logs: Sequence[StrengthSetLog]) -> StrengthSetLog:
    """La serie de más peso; a igual peso (o sin peso), la de más repeticiones o segundos."""
    return max(
        logs,
        key=lambda log: (
            log.weight_kg if log.weight_kg is not None else Decimal(-1),
            log.reps if log.reps is not None else (log.seconds or 0),
        ),
    )


def summarize_session(
    performed_on: date,
    activity_id: uuid.UUID,
    logs: Sequence[StrengthSetLog],
) -> ExerciseSession:
    """Cifras de un ejercicio en una sesión a partir de sus series hechas (al menos una)."""
    reps = [log.reps for log in logs if log.reps is not None]
    seconds = [log.seconds for log in logs if log.seconds is not None]
    weights = [log.weight_kg for log in logs if log.weight_kg is not None]
    weighted = [
        log.reps * log.weight_kg
        for log in logs
        if log.reps is not None and log.weight_kg is not None
    ]
    best = _best_set(logs)
    planned = next((log.planned_workout_id for log in logs if log.planned_workout_id), None)
    return ExerciseSession(
        performed_on=performed_on,
        activity_id=activity_id,
        planned_workout_id=planned,
        sets=len(logs),
        total_reps=sum(reps) if reps else None,
        total_seconds=sum(seconds) if seconds else None,
        max_weight_kg=_float(max(weights)) if weights else None,
        volume_kg=round(float(sum(weighted, Decimal(0))), 1) if weighted else None,
        best_set_reps=best.reps,
        best_set_seconds=best.seconds,
    )


def _done_sets(
    session: Session, user_id: uuid.UUID, exercise_ids: Iterable[uuid.UUID] | None = None
) -> list[tuple[StrengthSetLog, uuid.UUID, datetime]]:
    """Series hechas en actividades de fuerza, con su actividad y su inicio, por fecha."""
    query = (
        sa.select(StrengthSetLog, Activity.id, Activity.start_at)
        .join(Activity, StrengthSetLog.activity_id == Activity.id)
        .where(
            StrengthSetLog.user_id == user_id,
            StrengthSetLog.completed.is_(True),
            Activity.user_id == user_id,
            Activity.sport == Sport.STRENGTH,
            Activity.duplicate_of_id.is_(None),
        )
        .order_by(Activity.start_at, Activity.id, StrengthSetLog.set_number)
    )
    if exercise_ids is not None:
        query = query.where(StrengthSetLog.exercise_id.in_(list(exercise_ids)))
    return [(log, activity_id, start_at) for log, activity_id, start_at in session.execute(query)]


def _sessions_by_exercise(
    session: Session, user_id: uuid.UUID, exercise_ids: Iterable[uuid.UUID] | None = None
) -> dict[uuid.UUID, list[ExerciseSession]]:
    tz = ZoneInfo(athlete_timezone(session, user_id))
    grouped: dict[uuid.UUID, dict[uuid.UUID, tuple[datetime, list[StrengthSetLog]]]] = {}
    for log, activity_id, start_at in _done_sets(session, user_id, exercise_ids):
        by_activity = grouped.setdefault(log.exercise_id, {})
        by_activity.setdefault(activity_id, (start_at, []))[1].append(log)
    return {
        exercise_id: [
            summarize_session(start_at.astimezone(tz).date(), activity_id, logs)
            for activity_id, (start_at, logs) in by_activity.items()
        ]
        for exercise_id, by_activity in grouped.items()
    }


def exercise_progress(
    session: Session, user_id: uuid.UUID, exercise_id: uuid.UUID
) -> ExerciseProgress:
    """Historial del ejercicio por sesión, de la más antigua a la más reciente. 404 si el
    ejercicio no existe o es de otro atleta."""
    exercise = get_exercise(session, user_id, exercise_id)
    sessions = _sessions_by_exercise(session, user_id, [exercise_id]).get(exercise_id, [])
    return ExerciseProgress(exercise=exercise, sessions=sessions)


def performed_exercises(session: Session, user_id: uuid.UUID) -> list[PerformedExercise]:
    """Ejercicios hechos en sesiones completadas, del último hecho al más antiguo (y por
    nombre a igual fecha)."""
    by_exercise = _sessions_by_exercise(session, user_id)
    if not by_exercise:
        return []
    exercises = {
        exercise.id: exercise
        for exercise in session.scalars(sa.select(Exercise).where(Exercise.id.in_(by_exercise)))
    }
    performed = [
        PerformedExercise(
            exercise=exercises[exercise_id],
            sessions=len(sessions),
            first_performed_on=sessions[0].performed_on,
            last_performed_on=sessions[-1].performed_on,
            last_max_weight_kg=sessions[-1].max_weight_kg,
        )
        for exercise_id, sessions in by_exercise.items()
    ]
    performed.sort(key=lambda item: item.exercise.name)
    performed.sort(key=lambda item: item.last_performed_on, reverse=True)
    return performed
