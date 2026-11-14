"""Calendario: carreras, eventos sociales, viajes, salud y no disponibilidad."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, json_column, str_enum, user_fk, uuid_pk


class EventKind(enum.StrEnum):
    RACE = "race"
    SOCIAL = "social"
    TRAVEL = "travel"
    HEALTH = "health"
    PERSONAL = "personal"
    UNAVAILABLE = "unavailable"


class TrainingImpact(enum.StrEnum):
    """Cómo debe tratar el coach el evento al planificar."""

    NONE = "none"
    REDUCE = "reduce"
    NO_TRAINING = "no_training"
    MOVE = "move"


class RaceDiscipline(enum.StrEnum):
    ROAD_CYCLING = "road_cycling"
    GRAVEL = "gravel"
    MTB = "mtb"
    TRAIL_RUNNING = "trail_running"
    ROAD_RUNNING = "road_running"
    OTHER = "other"


class RacePriority(enum.StrEnum):
    A = "A"
    B = "B"
    C = "C"


class EnrichmentStatus(enum.StrEnum):
    """Datos de la carrera completados automáticamente (p. ej. con n8n) y revisión del usuario."""

    NONE = "none"
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"


class CalendarEvent(TimestampMixin, Base):
    __tablename__ = "calendar_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    kind: Mapped[EventKind] = mapped_column(str_enum(EventKind, "event_kind"))
    title: Mapped[str] = mapped_column(sa.String(200))
    start_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    all_day: Mapped[bool] = mapped_column(server_default=sa.true())
    training_impact: Mapped[TrainingImpact] = mapped_column(
        str_enum(TrainingImpact, "training_impact"), server_default=TrainingImpact.NONE.value
    )
    notes: Mapped[str | None] = mapped_column(sa.Text)
    details: Mapped[dict[str, Any]] = json_column()

    __table_args__ = (
        sa.Index("ix_calendar_events_user_id_start_at", "user_id", "start_at"),
        sa.CheckConstraint("end_at IS NULL OR end_at >= start_at", name="end_after_start"),
    )


class Race(TimestampMixin, Base):
    """Datos específicos de un evento de tipo carrera (1:1 con calendar_events)."""

    __tablename__ = "races"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("calendar_events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = user_fk()
    discipline: Mapped[RaceDiscipline | None] = mapped_column(
        str_enum(RaceDiscipline, "race_discipline")
    )
    distance_m: Mapped[Decimal | None] = mapped_column(sa.Numeric(9, 1))
    ascent_m: Mapped[Decimal | None] = mapped_column(sa.Numeric(7, 1))
    priority: Mapped[RacePriority] = mapped_column(
        str_enum(RacePriority, "race_priority"), server_default=RacePriority.B.value
    )
    goal: Mapped[str | None] = mapped_column(sa.Text)
    enrichment_status: Mapped[EnrichmentStatus] = mapped_column(
        str_enum(EnrichmentStatus, "enrichment_status"), server_default=EnrichmentStatus.NONE.value
    )
    source_url: Mapped[str | None] = mapped_column(sa.Text)
