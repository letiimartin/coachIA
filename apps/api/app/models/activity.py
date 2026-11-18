"""Actividades realizadas (importadas de proveedores o subidas a mano)."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import Sport, TimestampMixin, json_column, str_enum, user_fk, uuid_pk


class ActivitySource(enum.StrEnum):
    WAHOO = "wahoo"
    STRAVA = "strava"
    SUUNTO = "suunto"
    GARMIN = "garmin"
    FILE = "file"
    MANUAL = "manual"


class LoadMethod(enum.StrEnum):
    """Cómo se calculó la carga.

    `power`, `heart_rate`, `pace` y `rpe` son TSS (o una estimación de TSS) de resistencia y
    suman en CTL/ATL. `session_rpe` es la carga de fuerza (minutos × RPE de la sesión, Foster):
    no es TSS y no suma nunca en `daily_load`.
    """

    POWER = "power"
    HEART_RATE = "heart_rate"
    PACE = "pace"
    RPE = "rpe"
    SESSION_RPE = "session_rpe"


class Activity(TimestampMixin, Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    source: Mapped[ActivitySource] = mapped_column(str_enum(ActivitySource, "activity_source"))
    external_id: Mapped[str | None] = mapped_column(sa.String(64))
    sport: Mapped[Sport] = mapped_column(str_enum(Sport, "sport"))
    sub_sport: Mapped[str | None] = mapped_column(sa.String(32))
    title: Mapped[str | None] = mapped_column(sa.String(200))
    start_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    timezone: Mapped[str | None] = mapped_column(sa.String(64))

    elapsed_s: Mapped[int | None]
    moving_s: Mapped[int | None]
    distance_m: Mapped[Decimal | None] = mapped_column(sa.Numeric(9, 1))
    ascent_m: Mapped[Decimal | None] = mapped_column(sa.Numeric(7, 1))
    calories: Mapped[int | None]
    avg_hr: Mapped[int | None]
    max_hr: Mapped[int | None]
    avg_power_w: Mapped[int | None]
    normalized_power_w: Mapped[int | None]
    avg_cadence: Mapped[int | None]
    avg_speed_mps: Mapped[Decimal | None] = mapped_column(sa.Numeric(6, 3))
    # RPE de la sesión (1-10), introducido por la atleta. Sin valor por defecto.
    rpe: Mapped[int | None] = mapped_column(sa.SmallInteger)

    # Métricas calculadas por el motor de métricas (nunca por el LLM).
    load: Mapped[Decimal | None] = mapped_column(sa.Numeric(6, 1))
    load_method: Mapped[LoadMethod | None] = mapped_column(str_enum(LoadMethod, "load_method"))
    intensity_factor: Mapped[Decimal | None] = mapped_column(sa.Numeric(4, 3))

    # Fichero FIT original en Supabase Storage y respuesta cruda del proveedor.
    fit_path: Mapped[str | None] = mapped_column(sa.Text)
    raw: Mapped[dict[str, Any]] = json_column()

    # Misma actividad registrada por dos dispositivos (p. ej. Wahoo y reloj Suunto).
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("activities.id", ondelete="SET NULL")
    )

    __table_args__ = (
        sa.UniqueConstraint("user_id", "source", "external_id"),
        sa.Index("ix_activities_user_id_start_at", "user_id", sa.text("start_at DESC")),
        sa.CheckConstraint("elapsed_s IS NULL OR elapsed_s >= 0", name="elapsed"),
        sa.CheckConstraint("distance_m IS NULL OR distance_m >= 0", name="distance"),
        sa.CheckConstraint("rpe IS NULL OR rpe BETWEEN 1 AND 10", name="rpe"),
    )
