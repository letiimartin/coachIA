"""Perfil del atleta, historial de umbrales y disponibilidad semanal."""

import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, json_column, str_enum, user_fk, uuid_pk


class Sex(enum.StrEnum):
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"


class ThresholdSource(enum.StrEnum):
    MANUAL = "manual"
    TEST = "test"
    ESTIMATED = "estimated"


class PreferredTime(enum.StrEnum):
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    ANY = "any"


class AthleteProfile(TimestampMixin, Base):
    """1:1 con auth.users. La FK a auth.users se crea en la migración (esquema de Supabase)."""

    __tablename__ = "athlete_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(sa.String(120))
    birth_date: Mapped[date | None]
    sex: Mapped[Sex | None] = mapped_column(str_enum(Sex, "sex"))
    height_cm: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 1))
    timezone: Mapped[str] = mapped_column(sa.String(64), server_default="Europe/Madrid")
    sports: Mapped[list[str]] = mapped_column(
        ARRAY(sa.String(32)), server_default=sa.text("'{}'::varchar[]")
    )
    # Modelo de zonas, unidades, idioma y otras preferencias sin estructura fija.
    preferences: Mapped[dict[str, Any]] = json_column()

    __table_args__ = (
        sa.CheckConstraint("height_cm IS NULL OR height_cm BETWEEN 100 AND 250", name="height"),
    )


class AthleteThreshold(TimestampMixin, Base):
    """Umbrales con fecha de vigencia: el TSS de marzo se calcula con el FTP de marzo.

    Las zonas no se guardan: se calculan a partir del umbral vigente y del modelo de zonas.

    Hay un LTHR por disciplina (`cycling_lthr_bpm`, `running_lthr_bpm`). `legacy_lthr_bpm` es
    el LTHR único anterior a #22: se conserva para que la autora decida a qué disciplina
    pertenecía cada valor, pero ningún cálculo lo usa.
    """

    __tablename__ = "athlete_thresholds"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    effective_from: Mapped[date]
    ftp_w: Mapped[int | None]
    cycling_lthr_bpm: Mapped[int | None]
    running_lthr_bpm: Mapped[int | None]
    legacy_lthr_bpm: Mapped[int | None]
    hr_max_bpm: Mapped[int | None]
    hr_rest_bpm: Mapped[int | None]
    threshold_pace_s_per_km: Mapped[Decimal | None] = mapped_column(sa.Numeric(6, 1))
    vo2max: Mapped[Decimal | None] = mapped_column(sa.Numeric(4, 1))
    weight_kg: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2))
    source: Mapped[ThresholdSource] = mapped_column(
        str_enum(ThresholdSource, "threshold_source"), server_default=ThresholdSource.MANUAL.value
    )
    notes: Mapped[str | None] = mapped_column(sa.Text)

    __table_args__ = (
        sa.UniqueConstraint("user_id", "effective_from"),
        sa.CheckConstraint("ftp_w IS NULL OR ftp_w BETWEEN 50 AND 700", name="ftp"),
        sa.CheckConstraint(
            "cycling_lthr_bpm IS NULL OR cycling_lthr_bpm BETWEEN 80 AND 230", name="cycling_lthr"
        ),
        sa.CheckConstraint(
            "running_lthr_bpm IS NULL OR running_lthr_bpm BETWEEN 80 AND 230", name="running_lthr"
        ),
        sa.CheckConstraint(
            "legacy_lthr_bpm IS NULL OR legacy_lthr_bpm BETWEEN 80 AND 230", name="legacy_lthr"
        ),
        sa.CheckConstraint("hr_max_bpm IS NULL OR hr_max_bpm BETWEEN 100 AND 240", name="hr_max"),
        sa.CheckConstraint("hr_rest_bpm IS NULL OR hr_rest_bpm BETWEEN 25 AND 120", name="hr_rest"),
        sa.CheckConstraint("weight_kg IS NULL OR weight_kg BETWEEN 25 AND 250", name="weight"),
    )


class AvailabilitySlot(TimestampMixin, Base):
    """Disponibilidad habitual por día de la semana (0 = lunes)."""

    __tablename__ = "availability_slots"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    weekday: Mapped[int] = mapped_column(sa.SmallInteger)
    max_minutes: Mapped[int | None]
    sports: Mapped[list[str]] = mapped_column(
        ARRAY(sa.String(32)), server_default=sa.text("'{}'::varchar[]")
    )
    preferred_time: Mapped[PreferredTime] = mapped_column(
        str_enum(PreferredTime, "preferred_time"), server_default=PreferredTime.ANY.value
    )
    is_preferred_rest: Mapped[bool] = mapped_column(server_default=sa.false())

    __table_args__ = (
        sa.UniqueConstraint("user_id", "weekday"),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday"),
        sa.CheckConstraint("max_minutes IS NULL OR max_minutes BETWEEN 0 AND 1440", name="minutes"),
    )
