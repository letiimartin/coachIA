"""Entrenos planificados y fuerza (#30): catálogo, sesiones, registro de series y completar.

Todo se filtra por el atleta: un entreno de otro atleta responde 404, y sólo se ven los
ejercicios del sistema y los propios.

Completar una sesión de fuerza crea la `activity` (`sport = strength`, `source = manual`, con
duración y `rpe`) en la misma transacción que marca el entreno como hecho y asigna la actividad
a sus series. Su carga es `session_rpe` (minutos × RPE, #22): la calcula el gancho normal de
`fitness`, y no suma nunca en CTL/ATL/TSB.

La generación de sesiones por el coach llega en Fuerza 5: `create_strength_workout` es la
pieza que usará (y la que usan los tests); no tiene endpoint.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.core.text import search_key, search_text
from app.models import (
    Activity,
    ActivitySource,
    Exercise,
    ExerciseMode,
    ExerciseOrigin,
    MuscleGroup,
    PlannedStrengthExercise,
    PlannedWorkout,
    PlannedWorkoutStatus,
    Sport,
    StrengthSetLog,
)
from app.schemas.strength import StrengthSetIn
from app.services import fitness
from app.services.athletes import athlete_timezone, ensure_athlete_profile

SEARCH_LIMIT = 50

_STATUS_TEXT = {
    PlannedWorkoutStatus.PLANNED: "planificado",
    PlannedWorkoutStatus.DONE: "hecho",
    PlannedWorkoutStatus.SKIPPED: "saltado",
}


# --- Catálogo --------------------------------------------------------------------------------


def _visible_to(user_id: uuid.UUID) -> sa.ColumnElement[bool]:
    return sa.or_(Exercise.user_id.is_(None), Exercise.user_id == user_id)


def search_exercises(
    session: Session, user_id: uuid.UUID, query: str | None = None, limit: int = SEARCH_LIMIT
) -> list[Exercise]:
    """Ejercicios del sistema y propios cuyo nombre o alias contiene `query`.

    Sin distinguir mayúsculas, acentos ni signos («peso muerto», «PESO-MUERTO», «pesó muerto»).
    Primero los que empiezan por la búsqueda; después, por nombre. Sin `query`, todos.
    """
    statement = sa.select(Exercise).where(_visible_to(user_id))
    key = search_key(query or "")
    if key:
        # La clave normalizada sólo tiene letras, números y espacios: sin comodines de LIKE.
        statement = statement.where(Exercise.search_text.contains(key, autoescape=True))
        prefix = sa.or_(
            Exercise.search_text.startswith(key, autoescape=True),
            Exercise.search_text.contains(f"|{key}", autoescape=True),
        )
        statement = statement.order_by(sa.case((prefix, 0), else_=1))
    return list(session.scalars(statement.order_by(Exercise.name, Exercise.id).limit(limit)))


def get_exercise(session: Session, user_id: uuid.UUID, exercise_id: uuid.UUID) -> Exercise:
    exercise = session.scalar(
        sa.select(Exercise).where(Exercise.id == exercise_id, _visible_to(user_id))
    )
    if exercise is None:
        raise NotFoundError("Ejercicio no encontrado.")
    return exercise


def create_exercise(
    session: Session,
    user_id: uuid.UUID,
    *,
    slug: str,
    name: str,
    muscle_group: MuscleGroup,
    mode: ExerciseMode,
    origin: ExerciseOrigin = ExerciseOrigin.COACH,
    aliases: Sequence[str] = (),
) -> Exercise:
    """Ejercicio propio de la atleta (`coach` o `user`). Sin commit. Lo usará el coach."""
    if origin == ExerciseOrigin.SYSTEM:
        raise ValueError("Los ejercicios del sistema sólo se añaden con migraciones.")
    ensure_athlete_profile(session, user_id)
    exercise = Exercise(
        user_id=user_id,
        slug=slug,
        name=name,
        aliases=list(aliases),
        muscle_group=muscle_group,
        mode=mode,
        origin=origin,
        search_text=search_text(name, list(aliases)),
    )
    session.add(exercise)
    session.flush()
    return exercise


# --- Entrenos planificados -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlannedWorkoutSummary:
    """Entreno planificado con su número de ejercicios (0 si no es de fuerza)."""

    workout: PlannedWorkout
    exercise_count: int


def list_planned_workouts(
    session: Session, user_id: uuid.UUID, start: date, end: date
) -> list[PlannedWorkoutSummary]:
    """Entrenos planificados entre `start` y `end` (incluidos), por fecha y creación."""
    exercise_count = (
        sa.select(sa.func.count())
        .where(PlannedStrengthExercise.planned_workout_id == PlannedWorkout.id)
        .correlate(PlannedWorkout)
        .scalar_subquery()
    )
    rows = session.execute(
        sa.select(PlannedWorkout, exercise_count)
        .where(
            PlannedWorkout.user_id == user_id,
            PlannedWorkout.scheduled_on >= start,
            PlannedWorkout.scheduled_on <= end,
        )
        .order_by(PlannedWorkout.scheduled_on, PlannedWorkout.created_at, PlannedWorkout.id)
    ).all()
    return [PlannedWorkoutSummary(workout, count) for workout, count in rows]


@dataclass(frozen=True, slots=True)
class PlannedExerciseIn:
    """Ejercicio de una sesión al crearla. Exactamente uno de `target_reps`/`target_seconds`."""

    exercise_id: uuid.UUID
    sets: int
    target_reps: int | None = None
    target_seconds: int | None = None
    target_weight_kg: Decimal | None = None
    target_rpe: int | None = None
    target_rir: int | None = None
    notes: str | None = None


def _check_mode(exercise: Exercise, reps: int | None, seconds: int | None, what: str) -> None:
    expected_reps = exercise.mode == ExerciseMode.REPS
    if (reps is not None) != expected_reps or (seconds is not None) == expected_reps:
        unit = "repeticiones" if expected_reps else "segundos"
        raise UnprocessableError(
            f"{what}: «{exercise.name}» se mide en {unit}.",
            code="mode_mismatch",
            details={"exercise_id": str(exercise.id), "mode": exercise.mode.value},
        )


def _exercises_by_id(
    session: Session, user_id: uuid.UUID, ids: set[uuid.UUID]
) -> dict[uuid.UUID, Exercise]:
    """Ejercicios visibles para el atleta. 422 `unknown_exercise` si falta alguno."""
    found = {
        exercise.id: exercise
        for exercise in session.scalars(
            sa.select(Exercise).where(Exercise.id.in_(ids), _visible_to(user_id))
        )
    }
    missing = sorted(str(exercise_id) for exercise_id in ids - found.keys())
    if missing:
        raise UnprocessableError(
            "Hay ejercicios que no existen en el catálogo.",
            code="unknown_exercise",
            details={"exercise_ids": missing},
        )
    return found


def create_strength_workout(
    session: Session,
    user_id: uuid.UUID,
    *,
    scheduled_on: date,
    title: str,
    exercises: Sequence[PlannedExerciseIn],
    coach_reason: str | None = None,
    planned_duration_s: int | None = None,
) -> PlannedWorkout:
    """Crea una sesión de fuerza planificada con sus ejercicios, en orden. Sin commit."""
    ensure_athlete_profile(session, user_id)
    catalog = _exercises_by_id(session, user_id, {item.exercise_id for item in exercises})
    for item in exercises:
        _check_mode(catalog[item.exercise_id], item.target_reps, item.target_seconds, "Objetivo")
    workout = PlannedWorkout(
        user_id=user_id,
        sport=Sport.STRENGTH,
        scheduled_on=scheduled_on,
        title=title,
        coach_reason=coach_reason,
        planned_duration_s=planned_duration_s,
        status=PlannedWorkoutStatus.PLANNED,
    )
    session.add(workout)
    session.flush()
    session.add_all(
        PlannedStrengthExercise(
            user_id=user_id,
            planned_workout_id=workout.id,
            position=position,
            exercise_id=item.exercise_id,
            sets=item.sets,
            target_reps=item.target_reps,
            target_seconds=item.target_seconds,
            target_weight_kg=item.target_weight_kg,
            target_rpe=item.target_rpe,
            target_rir=item.target_rir,
            notes=item.notes,
        )
        for position, item in enumerate(exercises, start=1)
    )
    session.flush()
    return workout


# --- Sesión de fuerza ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StrengthWorkoutDetail:
    workout: PlannedWorkout
    exercises: list[tuple[PlannedStrengthExercise, Exercise]]
    set_logs: list[StrengthSetLog]
    activity: Activity | None


def _strength_workout(
    session: Session, user_id: uuid.UUID, workout_id: uuid.UUID, *, for_update: bool = False
) -> PlannedWorkout:
    """404 si no es del atleta; 422 `not_strength` si no es de fuerza."""
    query = sa.select(PlannedWorkout).where(
        PlannedWorkout.id == workout_id, PlannedWorkout.user_id == user_id
    )
    if for_update:
        query = query.with_for_update()
    workout = session.scalar(query)
    if workout is None:
        raise NotFoundError("Entreno planificado no encontrado.")
    if workout.sport != Sport.STRENGTH:
        raise UnprocessableError("El entreno no es de fuerza.", code="not_strength")
    return workout


def _planned_exercises(
    session: Session, workout_id: uuid.UUID
) -> list[tuple[PlannedStrengthExercise, Exercise]]:
    rows = session.execute(
        sa.select(PlannedStrengthExercise, Exercise)
        .join(Exercise, Exercise.id == PlannedStrengthExercise.exercise_id)
        .where(PlannedStrengthExercise.planned_workout_id == workout_id)
        .order_by(PlannedStrengthExercise.position)
    ).all()
    return [(planned, exercise) for planned, exercise in rows]


def _detail(session: Session, workout: PlannedWorkout) -> StrengthWorkoutDetail:
    exercises = _planned_exercises(session, workout.id)
    position = {planned.id: planned.position for planned, _ in exercises}
    logs = session.scalars(
        sa.select(StrengthSetLog).where(StrengthSetLog.planned_workout_id == workout.id)
    ).all()
    extra = max(position.values(), default=0) + 1

    def order(log: StrengthSetLog) -> tuple[int, str, int]:
        if log.planned_exercise_id is not None and log.planned_exercise_id in position:
            return position[log.planned_exercise_id], "", log.set_number
        return extra, str(log.exercise_id), log.set_number

    ordered = sorted(logs, key=order)
    activity = None if workout.activity_id is None else session.get(Activity, workout.activity_id)
    return StrengthWorkoutDetail(workout, exercises, ordered, activity)


def get_strength_workout(
    session: Session, user_id: uuid.UUID, workout_id: uuid.UUID
) -> StrengthWorkoutDetail:
    return _detail(session, _strength_workout(session, user_id, workout_id))


def _set_rows(
    session: Session,
    user_id: uuid.UUID,
    workout: PlannedWorkout,
    sets: Sequence[StrengthSetIn],
) -> list[StrengthSetLog]:
    """Valida las series y construye las filas. Lanza los 422 de `replace_sets`."""
    planned = {item.id: item for item, _ in _planned_exercises(session, workout.id)}
    unknown = sorted(
        {str(item.planned_exercise_id) for item in sets if item.planned_exercise_id is not None}
        - {str(planned_id) for planned_id in planned}
    )
    if unknown:
        raise UnprocessableError(
            "Hay series de ejercicios que no están en esta sesión.",
            code="unknown_planned_exercise",
            details={"planned_exercise_ids": unknown},
        )

    def exercise_of(item: StrengthSetIn) -> uuid.UUID:
        if item.exercise_id is not None:
            return item.exercise_id
        if item.planned_exercise_id is None:  # El schema exige uno de los dos.
            raise ValueError("Serie sin ejercicio.")
        return planned[item.planned_exercise_id].exercise_id

    catalog = _exercises_by_id(session, user_id, {exercise_of(item) for item in sets})
    seen: set[tuple[uuid.UUID | None, uuid.UUID, int]] = set()
    rows: list[StrengthSetLog] = []
    for item in sets:
        exercise_id = exercise_of(item)
        key = (item.planned_exercise_id, exercise_id, item.set_number)
        if key in seen:
            raise UnprocessableError(
                f"La serie {item.set_number} está repetida.",
                code="duplicate_set",
                details={
                    "planned_exercise_id": None
                    if item.planned_exercise_id is None
                    else str(item.planned_exercise_id),
                    "exercise_id": str(exercise_id),
                    "set_number": item.set_number,
                },
            )
        seen.add(key)
        _check_mode(catalog[exercise_id], item.reps, item.seconds, f"Serie {item.set_number}")
        rows.append(
            StrengthSetLog(
                user_id=user_id,
                activity_id=workout.activity_id,
                planned_workout_id=workout.id,
                exercise_id=exercise_id,
                planned_exercise_id=item.planned_exercise_id,
                set_number=item.set_number,
                reps=item.reps,
                seconds=item.seconds,
                weight_kg=item.weight_kg,
                rpe=item.rpe,
                rir=item.rir,
                completed=item.completed,
            )
        )
    return rows


def replace_sets(
    session: Session, user_id: uuid.UUID, workout_id: uuid.UUID, sets: Sequence[StrengthSetIn]
) -> StrengthWorkoutDetail:
    """Sustituye todas las series de la sesión por `sets`.

    Si la sesión ya está completada, las series nuevas llevan su actividad. 409 si el entreno
    está saltado. 422 con `code`: `not_strength`, `unknown_planned_exercise`,
    `unknown_exercise`, `mode_mismatch` (repeticiones en un ejercicio por segundos o al revés)
    y `duplicate_set`.
    """
    try:
        workout = _strength_workout(session, user_id, workout_id, for_update=True)
        if workout.status == PlannedWorkoutStatus.SKIPPED:
            raise ConflictError("El entreno está marcado como saltado.")
        rows = _set_rows(session, user_id, workout, sets)
    except Exception:
        session.rollback()  # Libera el bloqueo del entreno.
        raise
    session.execute(
        sa.delete(StrengthSetLog).where(StrengthSetLog.planned_workout_id == workout.id)
    )
    session.add_all(rows)
    workout.updated_at = sa.func.now()
    session.commit()
    session.refresh(workout)
    return _detail(session, workout)


def complete_workout(
    session: Session,
    user_id: uuid.UUID,
    workout_id: uuid.UUID,
    *,
    started_at: datetime,
    duration_s: int,
    rpe: int | None,
) -> StrengthWorkoutDetail:
    """Completa la sesión: crea la actividad de fuerza y marca el entreno como hecho.

    En la misma transacción: crea la `activity` (`sport = strength`, `source = manual`,
    duración y `rpe`), le asigna las series registradas, marca el entreno `done` con su
    `activity_id` y calcula la carga `session_rpe` con el gancho normal (que regenera la forma
    desde ese día; la fuerza no suma en CTL/ATL/TSB). Sin `rpe` (#52) no hay carga: queda
    vacía, sin RPE por defecto. 409 si ya está hecho o saltado.
    """
    workout = _strength_workout(session, user_id, workout_id, for_update=True)
    if workout.status != PlannedWorkoutStatus.PLANNED:
        session.rollback()
        raise ConflictError(f"El entreno ya está {_STATUS_TEXT[workout.status]}.")
    activity = Activity(
        user_id=user_id,
        source=ActivitySource.MANUAL,
        sport=Sport.STRENGTH,
        title=workout.title,
        start_at=started_at,
        timezone=athlete_timezone(session, user_id),
        elapsed_s=duration_s,
        moving_s=duration_s,
        rpe=rpe,
    )
    session.add(activity)
    session.flush()
    session.execute(
        sa.update(StrengthSetLog)
        .where(StrengthSetLog.planned_workout_id == workout.id)
        .values(activity_id=activity.id, updated_at=sa.func.now())
    )
    workout.status = PlannedWorkoutStatus.DONE
    workout.activity_id = activity.id
    workout.updated_at = sa.func.now()
    session.flush()
    fitness.recompute_since_activity(session, user_id, started_at)
    session.commit()
    session.refresh(workout)
    return _detail(session, workout)


# --- Historial -------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExerciseLastLog:
    exercise: Exercise
    performed_on: date | None
    activity_id: uuid.UUID | None
    planned_workout_id: uuid.UUID | None
    sets: list[StrengthSetLog]


def _before_reference(
    session: Session, user_id: uuid.UUID, workout_id: uuid.UUID
) -> list[sa.ColumnElement[bool]]:
    """Condiciones para quedarse con las sesiones anteriores al entreno `workout_id` (#52).

    Nunca cuenta el propio entreno. Si está completado, la referencia es el inicio de su
    actividad; si está hecho pero su actividad se borró, el comienzo de su día. Si aún no se ha
    hecho (o se saltó), cualquier sesión completada es anterior. 404 si no es del atleta.
    """
    workout = session.scalar(
        sa.select(PlannedWorkout).where(
            PlannedWorkout.id == workout_id, PlannedWorkout.user_id == user_id
        )
    )
    if workout is None:
        raise NotFoundError("Entreno planificado no encontrado.")
    conditions: list[sa.ColumnElement[bool]] = [
        sa.or_(
            StrengthSetLog.planned_workout_id.is_(None),
            StrengthSetLog.planned_workout_id != workout.id,
        )
    ]
    if workout.status != PlannedWorkoutStatus.DONE:
        return conditions
    reference = None if workout.activity_id is None else session.get(Activity, workout.activity_id)
    if reference is not None:
        conditions.append(Activity.start_at < reference.start_at)
    else:
        tz = ZoneInfo(athlete_timezone(session, user_id))
        day_start = datetime.combine(workout.scheduled_on, time.min, tzinfo=tz)
        conditions.append(Activity.start_at < day_start)
    return conditions


def last_log(
    session: Session,
    user_id: uuid.UUID,
    exercise_id: uuid.UUID,
    *,
    before_workout_id: uuid.UUID | None = None,
) -> ExerciseLastLog:
    """Series del ejercicio en la última sesión completada (con actividad) en que se registró.

    Con `before_workout_id`, la última anterior a ese entreno (ver `_before_reference`).
    404 si el ejercicio no existe o no es visible para el atleta, o si el entreno no es suyo.
    Si no hay registros, la fecha es null y no hay series.
    """
    exercise = get_exercise(session, user_id, exercise_id)
    conditions = (
        [] if before_workout_id is None else _before_reference(session, user_id, before_workout_id)
    )
    latest = session.execute(
        sa.select(Activity.id, Activity.start_at)
        .join(StrengthSetLog, StrengthSetLog.activity_id == Activity.id)
        .where(
            StrengthSetLog.user_id == user_id,
            StrengthSetLog.exercise_id == exercise_id,
            Activity.user_id == user_id,
            *conditions,
        )
        .order_by(Activity.start_at.desc(), Activity.id.desc())
        .limit(1)
    ).first()
    if latest is None:
        return ExerciseLastLog(exercise, None, None, None, [])
    activity_id, start_at = latest
    sets = list(
        session.scalars(
            sa.select(StrengthSetLog)
            .where(
                StrengthSetLog.activity_id == activity_id,
                StrengthSetLog.exercise_id == exercise_id,
            )
            .order_by(StrengthSetLog.set_number, StrengthSetLog.created_at)
        )
    )
    tz = ZoneInfo(athlete_timezone(session, user_id))
    return ExerciseLastLog(
        exercise=exercise,
        performed_on=start_at.astimezone(tz).date(),
        activity_id=activity_id,
        planned_workout_id=sets[0].planned_workout_id if sets else None,
        sets=sets,
    )
