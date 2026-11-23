"""Datos del coach desde la BD, siempre filtrados por la atleta.

Reutiliza los servicios existentes y devuelve resúmenes compactos: números redondeados,
duraciones en minutos y ritmos en min/km. Los valores derivados (carga, CTL/ATL/TSB, zonas)
son los que calcula el sistema; el coach nunca los calcula.
"""

import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.coach import memory as coach_memory
from app.coach.tools import MemoryProposal
from app.core.errors import NotFoundError, UnprocessableError
from app.models import (
    Activity,
    AthleteProfile,
    PlannedStrengthExercise,
    PlannedWorkout,
    PlannedWorkoutStatus,
    Sport,
)
from app.models.calendar import EventKind, RacePriority
from app.schemas.athlete import ZoneOut
from app.services import availability, calendar, fitness, strength, thresholds
from app.services.athletes import athlete_timezone

_WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MAX_ACTIVITIES = 40
_MAX_STRENGTH_DETAILS = 4


def _num(value: Decimal | float | int | None, digits: int = 1) -> float | int | None:
    if value is None:
        return None
    rounded = round(float(value), digits)
    return int(rounded) if rounded.is_integer() else rounded


def _minutes(seconds: int | None) -> int | None:
    return None if seconds is None else round(seconds / 60)


def pace(seconds_per_km: float | None) -> str | None:
    if seconds_per_km is None:
        return None
    total = round(seconds_per_km)
    return f"{total // 60}:{total % 60:02d}/km"


def _zones(zones: list[ZoneOut] | None, unit: str) -> list[str] | None:
    if zones is None:
        return None

    def fmt(value: float | None) -> str:
        if value is None:
            return "∞"
        return pace(value) or "" if unit == "pace" else str(round(value))

    suffix = "" if unit == "pace" else f" {unit}"
    return [f"{z.code} {z.name}: {fmt(z.low)}–{fmt(z.high)}{suffix}" for z in zones]


def age_on(birth_date: date | None, today: date) -> int | None:
    if birth_date is None:
        return None
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


class DbCoachData:
    """`CoachData` sobre la BD para una atleta, una conversación y el mensaje en curso."""

    def __init__(
        self,
        session: Session,
        user_id: uuid.UUID,
        *,
        today: date,
        conversation_id: uuid.UUID | None = None,
        user_message_id: uuid.UUID | None = None,
    ):
        self.session = session
        self.user_id = user_id
        self.today = today
        self.conversation_id = conversation_id
        self.user_message_id = user_message_id
        self.tz = ZoneInfo(athlete_timezone(session, user_id))
        # Ids de las propuestas de memoria creadas en esta respuesta.
        self.proposed_memory_ids: list[uuid.UUID] = []

    # --- Lectura ---------------------------------------------------------------------------

    def profile(self) -> dict[str, Any]:
        profile = self.session.get(AthleteProfile, self.user_id)
        threshold = thresholds.threshold_on(self.session, self.user_id, self.today)
        result: dict[str, Any] = {
            "today": f"{self.today.isoformat()} ({_WEEKDAYS[self.today.weekday()]})",
            "profile": None
            if profile is None
            else {
                "name": profile.display_name,
                "sex": profile.sex,
                "age": age_on(profile.birth_date, self.today),
                "height_cm": _num(profile.height_cm),
                "timezone": profile.timezone,
                "sports": profile.sports,
            },
            "thresholds": None,
            "zones": None,
        }
        if threshold is None:
            return result
        result["thresholds"] = {
            "effective_from": threshold.effective_from,
            "source": threshold.source,
            "ftp_w": threshold.ftp_w,
            "cycling_lthr_bpm": threshold.cycling_lthr_bpm,
            "running_lthr_bpm": threshold.running_lthr_bpm,
            "hr_max_bpm": threshold.hr_max_bpm,
            "hr_rest_bpm": threshold.hr_rest_bpm,
            "threshold_pace": pace(
                None
                if threshold.threshold_pace_s_per_km is None
                else float(threshold.threshold_pace_s_per_km)
            ),
            "vo2max": _num(threshold.vo2max),
            "weight_kg": _num(threshold.weight_kg),
        }
        zones = thresholds.zones_for(threshold)
        result["zones"] = {
            key: value
            for key, value in {
                "cycling_power": _zones(zones.power, "W"),
                "cycling_hr": _zones(zones.hr_cycling, "ppm"),
                "running_pace": _zones(zones.running_pace, "pace"),
                "running_hr": _zones(zones.hr_running, "ppm"),
                "trail_hr": _zones(zones.trail_hr, "ppm"),
            }.items()
            if value is not None
        }
        return result

    def fitness(self, days: int) -> dict[str, Any]:
        start = self.today - timedelta(days=max(days, 28))
        series = fitness.fitness_range(self.session, self.user_id, start, self.today)
        if not series or all(d.ctl == 0 and d.atl == 0 for d in series):
            return {"today": self.today, "available": False}
        by_day = {d.day: d for d in series}
        current = by_day[self.today]

        def ctl_on(offset: int) -> float | int | None:
            day = by_day.get(self.today - timedelta(days=offset))
            return None if day is None else _num(day.ctl)

        recent = [d for d in series if d.day > self.today - timedelta(days=days)]
        return {
            "today": self.today,
            "available": True,
            "ctl": _num(current.ctl),
            "atl": _num(current.atl),
            "tsb": _num(current.tsb),
            "ctl_7_days_ago": ctl_on(7),
            "ctl_28_days_ago": ctl_on(28),
            "load_last_7_days": _num(
                sum(d.load for d in series if d.day > self.today - timedelta(days=7))
            ),
            "daily_load": [
                {"day": d.day, "load": _num(d.load), "tsb": _num(d.tsb)} for d in recent if d.load
            ],
            "note": "TSB = CTL − ATL del día anterior. Carga en TSS; la fuerza no suma.",
        }

    def recent_activities(self, days: int) -> dict[str, Any]:
        since = datetime.combine(self.today - timedelta(days=days - 1), time.min, tzinfo=self.tz)
        rows = self.session.scalars(
            sa.select(Activity)
            .where(
                Activity.user_id == self.user_id,
                Activity.start_at >= since,
                Activity.duplicate_of_id.is_(None),
            )
            .order_by(Activity.start_at.desc())
            .limit(_MAX_ACTIVITIES)
        ).all()
        return {
            "days": days,
            "count": len(rows),
            "activities": [
                {
                    k: v
                    for k, v in {
                        "date": a.start_at.astimezone(self.tz).date(),
                        "sport": a.sport,
                        "title": a.title,
                        "duration_min": _minutes(a.moving_s or a.elapsed_s),
                        "distance_km": None
                        if a.distance_m is None
                        else _num(float(a.distance_m) / 1000),
                        "ascent_m": _num(a.ascent_m, 0),
                        "load": _num(a.load),
                        "load_method": a.load_method,
                        "rpe": a.rpe,
                        "avg_hr": a.avg_hr,
                        "avg_power_w": a.avg_power_w,
                        "np_w": a.normalized_power_w,
                    }.items()
                    if v is not None
                }
                for a in rows
            ],
        }

    def calendar(self, days_ahead: int) -> dict[str, Any]:
        events = calendar.list_events(
            self.session, self.user_id, self.today, self.today + timedelta(days=days_ahead)
        )
        items = []
        for event in events:
            item: dict[str, Any] = {
                "id": event.id,
                "kind": event.kind,
                "title": event.title,
                "start": event.start_at.astimezone(self.tz).date(),
                "end": None if event.end_at is None else event.end_at.astimezone(self.tz).date(),
                "training_impact": event.training_impact,
            }
            if event.notes:
                item["notes"] = event.notes[:300]
            if event.race is not None:
                item["race"] = {
                    "priority": event.race.priority,
                    "discipline": event.race.discipline,
                    "distance_km": None
                    if event.race.distance_m is None
                    else _num(event.race.distance_m / 1000),
                    "ascent_m": _num(event.race.ascent_m, 0),
                    "goal": event.race.goal,
                }
            items.append(item)
        races = [i for i in items if i["kind"] == EventKind.RACE]
        goal = next(
            (r for r in races if r["race"]["priority"] == RacePriority.A),
            races[0] if races else None,
        )
        return {
            "from": self.today,
            "days_ahead": days_ahead,
            "events": items,
            "next_goal_race": None
            if goal is None
            else {**goal, "days_until": (goal["start"] - self.today).days},
        }

    def planned_workouts(self, days_back: int, days_ahead: int) -> dict[str, Any]:
        summaries = strength.list_planned_workouts(
            self.session,
            self.user_id,
            self.today - timedelta(days=days_back),
            self.today + timedelta(days=days_ahead),
        )
        items = []
        details = 0
        for summary in summaries:
            w = summary.workout
            item: dict[str, Any] = {
                "id": w.id,
                "date": w.scheduled_on,
                "sport": w.sport,
                "title": w.title,
                "status": w.status,
                "planned_min": _minutes(w.planned_duration_s),
                "actual_min": _minutes(summary.actual_duration_s),
            }
            if w.coach_reason:
                item["coach_reason"] = w.coach_reason[:300]
            if w.missed_reason:
                item["missed_reason"] = w.missed_reason
            if (
                w.sport == Sport.STRENGTH
                and summary.exercise_count
                and details < _MAX_STRENGTH_DETAILS
                and w.scheduled_on >= self.today - timedelta(days=1)
            ):
                item["exercises"] = self._strength_exercises(w)
                details += 1
            items.append({k: v for k, v in item.items() if v is not None})
        return {"today": self.today, "workouts": items}

    def _strength_exercises(self, workout: PlannedWorkout) -> list[dict[str, Any]]:
        detail = strength.get_strength_workout(self.session, self.user_id, workout.id)
        result = []
        for planned, exercise in detail.exercises:
            last = strength.last_log(
                self.session, self.user_id, exercise.id, before_workout_id=workout.id
            )
            result.append(self._exercise_line(planned, exercise.name, last))
        return result

    @staticmethod
    def _exercise_line(
        planned: PlannedStrengthExercise, name: str, last: strength.ExerciseLastLog
    ) -> dict[str, Any]:
        target = (
            f"{planned.sets}×{planned.target_reps}"
            if planned.target_reps is not None
            else f"{planned.sets}×{planned.target_seconds}s"
        )
        line: dict[str, Any] = {"exercise": name, "target": target}
        if planned.target_weight_kg is not None:
            line["target_kg"] = _num(planned.target_weight_kg)
        if planned.target_rpe is not None:
            line["target_rpe"] = planned.target_rpe
        if planned.target_rir is not None:
            line["target_rir"] = planned.target_rir
        if last.performed_on is not None:
            line["last"] = {
                "date": last.performed_on,
                "sets": [
                    {
                        k: v
                        for k, v in {
                            "reps": s.reps,
                            "s": s.seconds,
                            "kg": _num(s.weight_kg),
                            "rpe": s.rpe,
                        }.items()
                        if v is not None
                    }
                    for s in last.sets
                ],
            }
        return line

    def availability(self) -> dict[str, Any]:
        week = availability.get_week(self.session, self.user_id)
        return {
            "days": [
                {
                    "day": _WEEKDAYS[d.weekday],
                    "max_min": d.max_minutes,
                    "sports": d.sports,
                    "time": d.preferred_time,
                    "rest": d.is_preferred_rest,
                }
                for d in week.days
            ]
        }

    def memory(self) -> dict[str, Any]:
        items = coach_memory.confirmed_memory(self.session, self.user_id)
        return {
            "confirmed": [
                {
                    "kind": m.kind,
                    "content": m.content,
                    "since": None
                    if m.confirmed_at is None
                    else m.confirmed_at.astimezone(self.tz).date(),
                }
                for m in items
            ]
        }

    # --- Registro --------------------------------------------------------------------------

    def propose_memory(self, items: list[MemoryProposal]) -> dict[str, Any]:
        if self.conversation_id is None:  # pragma: no cover - siempre hay conversación.
            raise UnprocessableError("No hay conversación.")
        created = coach_memory.propose(self.session, self.user_id, self.conversation_id, items)
        self.proposed_memory_ids = [m.id for m in created]
        return {
            "proposed": len(created),
            "status": "pendiente de que la atleta lo confirme en la app",
        }

    def record_missed_reason(self, workout_id: uuid.UUID, reason: str) -> dict[str, Any]:
        workout = self.session.scalar(
            sa.select(PlannedWorkout)
            .where(PlannedWorkout.id == workout_id, PlannedWorkout.user_id == self.user_id)
            .with_for_update()
        )
        if workout is None:
            raise NotFoundError("Entreno planificado no encontrado.")
        if workout.status == PlannedWorkoutStatus.DONE:
            raise UnprocessableError("El entreno está hecho: no tiene motivo de no hacerlo.")
        if workout.scheduled_on > self.today:
            raise UnprocessableError("El entreno es futuro: todavía no se ha dejado de hacer.")
        workout.missed_reason = reason
        workout.missed_reason_at = datetime.now(UTC)
        workout.missed_reason_message_id = self.user_message_id
        workout.updated_at = sa.func.now()
        self.session.flush()
        return {"saved": True, "workout_id": workout.id, "date": workout.scheduled_on}
