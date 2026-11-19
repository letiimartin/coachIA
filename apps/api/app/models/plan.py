"""Entrenos planificados (#30): la base común del futuro módulo de plan.

La fuerza es el primer tipo: sus ejercicios están en `planned_strength_exercises`. Cuando el
entreno se hace, `activity_id` apunta a la actividad que lo cumplió.
"""

import enum
import uuid
from datetime import date

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import Sport, TimestampMixin, str_enum, user_fk, uuid_pk


class PlannedWorkoutStatus(enum.StrEnum):
    PLANNED = "planned"
    DONE = "done"
    SKIPPED = "skipped"


class PlannedWorkout(TimestampMixin, Base):
    __tablename__ = "planned_workouts"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    sport: Mapped[Sport] = mapped_column(str_enum(Sport, "sport"))
    # Día local (zona horaria del atleta) para el que está planificado.
    scheduled_on: Mapped[date]
    title: Mapped[str] = mapped_column(sa.String(200))
    status: Mapped[PlannedWorkoutStatus] = mapped_column(
        str_enum(PlannedWorkoutStatus, "planned_workout_status"),
        server_default=PlannedWorkoutStatus.PLANNED.value,
    )
    # Por qué lo propone el coach (texto para la atleta).
    coach_reason: Mapped[str | None] = mapped_column(sa.Text)
    # Actividad que lo cumplió. SET NULL: borrar la actividad no borra el plan.
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("activities.id", ondelete="SET NULL"), unique=True
    )

    __table_args__ = (
        sa.Index("ix_planned_workouts_user_id_scheduled_on", "user_id", "scheduled_on"),
        sa.CheckConstraint("activity_id IS NULL OR status = 'done'", name="activity_done"),
    )
