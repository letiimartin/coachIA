"""Coach v1 (#55): conversaciones, mensajes, memoria confirmada y registro de llamadas al LLM.

- `coach_conversations`: una conversación de la atleta con el coach. `kind = intake` es la toma
  de contacto; está hecha cuando `intake_completed_at` tiene valor. `summary` es el resumen de
  los mensajes antiguos (hasta `summary_through_seq`), que mantiene el código con el LLM.
- `coach_messages`: los mensajes, numerados por conversación (`seq`). Los de la atleta
  (`user`), las respuestas (`assistant`), los resultados de herramientas (`tool`) y los avisos
  del sistema (`system`). `origin` dice de dónde sale una respuesta: el LLM, el filtro de
  seguridad o el límite de presupuesto (las dos últimas son fijas y no llaman al LLM).
- `coach_llm_calls`: cada llamada al LLM con sus tokens y su coste. Es la fuente del
  presupuesto mensual: cuenta la conversación, los resúmenes y, más adelante, el planificador.
- `coach_memory`: objetivos y preferencias. El coach sólo las **propone**; pasan a la memoria
  cuando la atleta las confirma (o las añade ella).
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, str_enum, user_fk, uuid_pk


class ConversationChannel(enum.StrEnum):
    APP = "app"


class ConversationKind(enum.StrEnum):
    INTAKE = "intake"  # Toma de contacto.
    CHAT = "chat"


class MessageRole(enum.StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class MessageOrigin(enum.StrEnum):
    """De dónde sale un mensaje que no escribe la atleta."""

    LLM = "llm"
    SAFETY_FILTER = "safety_filter"
    BUDGET_LIMIT = "budget_limit"
    TOOL = "tool"


class LlmCallPurpose(enum.StrEnum):
    CHAT = "chat"
    SUMMARY = "summary"
    PLANNER = "planner"


class MemoryKind(enum.StrEnum):
    GOAL = "goal"
    PREFERENCE = "preference"
    OTHER = "other"


class MemoryStatus(enum.StrEnum):
    PROPOSED = "proposed"  # Propuesta por el coach, pendiente de la atleta.
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"  # El coach la sustituyó por otra propuesta antes de confirmarla.


class MemorySource(enum.StrEnum):
    COACH = "coach"  # Propuesta por el coach y confirmada por la atleta.
    ATHLETE = "athlete"  # Añadida directamente por la atleta.


class CoachConversation(TimestampMixin, Base):
    __tablename__ = "coach_conversations"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    channel: Mapped[ConversationChannel] = mapped_column(
        str_enum(ConversationChannel, "conversation_channel"),
        server_default=ConversationChannel.APP.value,
    )
    kind: Mapped[ConversationKind] = mapped_column(str_enum(ConversationKind, "conversation_kind"))
    title: Mapped[str | None] = mapped_column(sa.String(200))
    # Resumen de los mensajes con `seq <= summary_through_seq` (0: no hay resumen).
    summary: Mapped[str | None] = mapped_column(sa.Text)
    summary_through_seq: Mapped[int] = mapped_column(server_default=sa.text("0"))
    last_message_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    # Toma de contacto terminada: la atleta ha revisado todo lo que propuso el coach.
    intake_completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    __table_args__ = (
        sa.Index("ix_coach_conversations_user_id_last_message_at", "user_id", "last_message_at"),
        sa.CheckConstraint("summary_through_seq >= 0", name="summary_through_seq"),
        sa.CheckConstraint(
            "intake_completed_at IS NULL OR kind = 'intake'", name="intake_completed"
        ),
    )


class CoachMessage(Base):
    __tablename__ = "coach_messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("coach_conversations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = user_fk()
    seq: Mapped[int]
    role: Mapped[MessageRole] = mapped_column(str_enum(MessageRole, "message_role"))
    origin: Mapped[MessageOrigin | None] = mapped_column(str_enum(MessageOrigin, "message_origin"))
    content: Mapped[str] = mapped_column(sa.Text)
    # Llamadas a herramientas: en `assistant`, las que hizo durante la respuesta; en `tool`, la
    # llamada cuyo resultado es `content`.
    tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(sa.String(64))
    tokens_in: Mapped[int | None]
    tokens_out: Mapped[int | None]
    cost_eur: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 6))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint("conversation_id", "seq"),
        sa.CheckConstraint("seq >= 1", name="seq"),
        sa.CheckConstraint("(role = 'user') = (origin IS NULL)", name="origin"),
        sa.CheckConstraint("tokens_in IS NULL OR tokens_in >= 0", name="tokens_in"),
        sa.CheckConstraint("tokens_out IS NULL OR tokens_out >= 0", name="tokens_out"),
        sa.CheckConstraint("cost_eur IS NULL OR cost_eur >= 0", name="cost"),
    )


class CoachLlmCall(Base):
    """Una llamada al LLM. Se conserva aunque se borre la conversación (cuenta en el mes)."""

    __tablename__ = "coach_llm_calls"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("coach_conversations.id", ondelete="SET NULL"),
        index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("coach_messages.id", ondelete="SET NULL"), index=True
    )
    purpose: Mapped[LlmCallPurpose] = mapped_column(str_enum(LlmCallPurpose, "llm_call_purpose"))
    provider: Mapped[str] = mapped_column(sa.String(32))
    model: Mapped[str] = mapped_column(sa.String(64))
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]
    cache_read_tokens: Mapped[int] = mapped_column(server_default=sa.text("0"))
    cache_write_tokens: Mapped[int] = mapped_column(server_default=sa.text("0"))
    cost_usd: Mapped[Decimal] = mapped_column(sa.Numeric(12, 6))
    cost_eur: Mapped[Decimal] = mapped_column(sa.Numeric(12, 6))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    __table_args__ = (
        sa.Index("ix_coach_llm_calls_user_id_created_at", "user_id", "created_at"),
        sa.CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND cache_read_tokens >= 0 "
            "AND cache_write_tokens >= 0",
            name="tokens",
        ),
        sa.CheckConstraint("cost_usd >= 0 AND cost_eur >= 0", name="cost"),
    )


class CoachMemory(TimestampMixin, Base):
    __tablename__ = "coach_memory"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    kind: Mapped[MemoryKind] = mapped_column(str_enum(MemoryKind, "memory_kind"))
    content: Mapped[str] = mapped_column(sa.Text)
    status: Mapped[MemoryStatus] = mapped_column(str_enum(MemoryStatus, "memory_status"))
    source: Mapped[MemorySource] = mapped_column(str_enum(MemorySource, "memory_source"))
    # Origen: la conversación y el mensaje del coach con el resumen que la propuso.
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("coach_conversations.id", ondelete="SET NULL"),
        index=True,
    )
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("coach_messages.id", ondelete="SET NULL")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    __table_args__ = (
        sa.Index("ix_coach_memory_user_id_status", "user_id", "status"),
        sa.CheckConstraint("(status = 'confirmed') = (confirmed_at IS NOT NULL)", name="confirmed"),
        sa.CheckConstraint("source = 'coach' OR status = 'confirmed'", name="athlete_confirmed"),
        sa.CheckConstraint("length(content) BETWEEN 1 AND 1000", name="content"),
    )
