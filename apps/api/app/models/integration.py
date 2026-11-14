"""Conexiones OAuth con proveedores externos (Wahoo, Strava…)."""

import enum
import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, json_column, str_enum, user_fk, uuid_pk


class Provider(enum.StrEnum):
    WAHOO = "wahoo"
    STRAVA = "strava"
    SUUNTO = "suunto"
    GARMIN = "garmin"


class IntegrationStatus(enum.StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    ERROR = "error"


class Integration(TimestampMixin, Base):
    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    provider: Mapped[Provider] = mapped_column(str_enum(Provider, "provider"))
    external_user_id: Mapped[str | None] = mapped_column(sa.String(64))
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(sa.String(64)), server_default=sa.text("'{}'::varchar[]")
    )
    # Tokens cifrados en la aplicación (nunca en claro); el cifrado llega con T4.
    access_token_enc: Mapped[str | None] = mapped_column(sa.Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(sa.Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    status: Mapped[IntegrationStatus] = mapped_column(
        str_enum(IntegrationStatus, "integration_status"),
        server_default=IntegrationStatus.ACTIVE.value,
    )
    last_error: Mapped[str | None] = mapped_column(sa.Text)
    last_sync_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    sync_cursor: Mapped[dict[str, Any]] = json_column()

    __table_args__ = (
        sa.UniqueConstraint("user_id", "provider"),
        sa.UniqueConstraint("provider", "external_user_id"),
    )
