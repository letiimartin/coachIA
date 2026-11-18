"""Propuestas de umbral salidas de un test (#42). Sólo propuestas: no cambian ningún umbral.

Al aceptarla se crea una fila nueva en `athlete_thresholds` (`source = test`) o, si ya hay una
en `test_date`, sólo se actualiza su FTP (#45); la propuesta guarda el id de esa fila y la fila
el de la propuesta (`ftp_proposal_id`). Al rechazarla no se toca nada más.
"""

import enum
import uuid
from datetime import date, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.metrics.tests import ThresholdProtocol
from app.models.common import TimestampMixin, json_column, str_enum, user_fk, uuid_pk


class ProposalStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AcceptAction(enum.StrEnum):
    """Qué hace aceptar una propuesta (#45). No se guarda: se calcula en la vista previa."""

    CREATE_ROW = "create_row"  # No hay umbrales en `test_date`: fila nueva `source = test`.
    UPDATE_FTP = "update_ftp"  # Ya hay una fila en `test_date`: sólo cambia su `ftp_w`.


class PreviewWarningCode(enum.StrEnum):
    LATER_THRESHOLDS = "later_thresholds"


class ThresholdProposal(TimestampMixin, Base):
    __tablename__ = "threshold_proposals"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("activities.id", ondelete="CASCADE"), index=True
    )
    protocol: Mapped[ThresholdProtocol] = mapped_column(
        str_enum(ThresholdProtocol, "threshold_protocol")
    )
    status: Mapped[ProposalStatus] = mapped_column(
        str_enum(ProposalStatus, "proposal_status"), server_default=ProposalStatus.PENDING.value
    )
    # Día local de la actividad (zona del atleta): será el `effective_from` si se acepta.
    test_date: Mapped[date]
    interval_start_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    interval_end_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    # Métricas del bloque detectado (potencia media y normalizada, FC, % de datos válidos…).
    metrics: Mapped[dict[str, Any]] = json_column()
    proposed_ftp_w: Mapped[int]
    # Avisos de calidad: criterios no bloqueantes que no se cumplen
    # ({code, passed, blocking, measured, threshold, comparison, unit, message}).
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, server_default=sa.text("'[]'::jsonb")
    )
    decided_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    # Umbral creado o actualizado al aceptar.
    # SET NULL: borrar ese umbral no borra el historial del test.
    threshold_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("athlete_thresholds.id", ondelete="SET NULL")
    )
    # Historial de la aceptación (#45), guardado en la misma transacción que cambia el umbral:
    # qué se hizo y el FTP de `test_date` justo antes (el de la fila con `update_ftp`, el
    # vigente ese día con `create_row`; null si no había). Sólo historial: nada lo usa.
    accepted_action: Mapped[AcceptAction | None] = mapped_column(
        str_enum(AcceptAction, "accept_action")
    )
    previous_ftp_w: Mapped[int | None]

    __table_args__ = (
        sa.CheckConstraint("proposed_ftp_w BETWEEN 50 AND 700", name="ftp"),
        sa.CheckConstraint("interval_end_at > interval_start_at", name="interval"),
        sa.CheckConstraint("(status = 'pending') = (decided_at IS NULL)", name="decided"),
        sa.CheckConstraint("threshold_id IS NULL OR status = 'accepted'", name="threshold"),
        sa.CheckConstraint(
            "(status = 'accepted') = (accepted_action IS NOT NULL)", name="accepted_history"
        ),
        sa.CheckConstraint("previous_ftp_w IS NULL OR status = 'accepted'", name="previous_ftp"),
        # Una sola propuesta pendiente por actividad y protocolo.
        sa.Index(
            "uq_threshold_proposals_pending",
            "activity_id",
            "protocol",
            unique=True,
            postgresql_where=sa.text("status = 'pending'"),
        ),
    )
