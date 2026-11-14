"""Tipos y columnas comunes a todos los modelos."""

import enum
import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column


def str_enum(enum_cls: type[enum.StrEnum], name: str) -> sa.Enum:
    """Enum guardado como texto con CHECK (más fácil de migrar que un ENUM nativo de Postgres)."""
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda members: [member.value for member in members],
    )


def user_fk() -> Mapped[uuid.UUID]:
    """Propietario de la fila: todo cuelga de athlete_profiles, que cuelga de auth.users."""
    return mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("athlete_profiles.user_id", ondelete="CASCADE"),
        index=True,
    )


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def json_column() -> Mapped[dict[str, Any]]:
    return mapped_column(JSONB, server_default=sa.text("'{}'::jsonb"))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class Sport(enum.StrEnum):
    CYCLING = "cycling"
    RUNNING = "running"
    TRAIL_RUNNING = "trail_running"
    HIKING = "hiking"
    STRENGTH = "strength"
    SWIMMING = "swimming"
    OTHER = "other"
