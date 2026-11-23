"""Memoria del coach: memoria confirmada (objetivos y preferencias) y resumen de la conversación.

**Memoria confirmada.** El coach sólo propone (`propose`); la atleta confirma, corrige, rechaza
o borra desde la app. Cada nueva propuesta del coach en una conversación sustituye a las que
seguían pendientes en ella (`superseded`). La toma de contacto queda hecha cuando la atleta ha
revisado todo lo que propuso el coach en ella.

**Resumen.** El contexto de cada respuesta son los últimos N mensajes y un resumen de los
anteriores. Cuando quedan al menos `coach_summary_batch` mensajes fuera de la ventana sin
resumir, el código pide al LLM que los incorpore al resumen (cuenta en el presupuesto).
"""

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.coach import budget
from app.coach.llm.base import ChatMessage, LLMError, LLMProvider, LLMUsage
from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError
from app.models import (
    CoachConversation,
    CoachMemory,
    CoachMessage,
    ConversationKind,
    LlmCallPurpose,
    MemoryKind,
    MemorySource,
    MemoryStatus,
    MessageRole,
)

if TYPE_CHECKING:
    from app.coach.tools import MemoryProposal

logger = logging.getLogger(__name__)

# --- Memoria confirmada ----------------------------------------------------------------------


def confirmed_memory(session: Session, user_id: uuid.UUID) -> list[CoachMemory]:
    return list(
        session.scalars(
            sa.select(CoachMemory)
            .where(CoachMemory.user_id == user_id, CoachMemory.status == MemoryStatus.CONFIRMED)
            .order_by(CoachMemory.confirmed_at, CoachMemory.id)
        )
    )


def list_memory(
    session: Session, user_id: uuid.UUID, status: MemoryStatus | None
) -> list[CoachMemory]:
    query = sa.select(CoachMemory).where(CoachMemory.user_id == user_id)
    if status is not None:
        query = query.where(CoachMemory.status == status)
    return list(session.scalars(query.order_by(CoachMemory.created_at, CoachMemory.id)))


def propose(
    session: Session,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    items: "Sequence[MemoryProposal]",
) -> list[CoachMemory]:
    """Crea propuestas pendientes (sin commit) y sustituye las pendientes de la conversación."""
    session.execute(
        sa.update(CoachMemory)
        .where(
            CoachMemory.user_id == user_id,
            CoachMemory.conversation_id == conversation_id,
            CoachMemory.status == MemoryStatus.PROPOSED,
        )
        .values(status=MemoryStatus.SUPERSEDED, updated_at=sa.func.now())
    )
    created = [
        CoachMemory(
            user_id=user_id,
            kind=item.kind,
            content=item.content.strip(),
            status=MemoryStatus.PROPOSED,
            source=MemorySource.COACH,
            conversation_id=conversation_id,
        )
        for item in items
    ]
    session.add_all(created)
    session.flush()
    return created


def attach_source_message(
    session: Session, memory_ids: Sequence[uuid.UUID], message_id: uuid.UUID
) -> None:
    if memory_ids:
        session.execute(
            sa.update(CoachMemory)
            .where(CoachMemory.id.in_(memory_ids))
            .values(source_message_id=message_id)
        )


def _get(session: Session, user_id: uuid.UUID, memory_id: uuid.UUID) -> CoachMemory:
    item = session.scalar(
        sa.select(CoachMemory)
        .where(CoachMemory.id == memory_id, CoachMemory.user_id == user_id)
        .with_for_update()
    )
    if item is None:
        raise NotFoundError("Elemento de memoria no encontrado.")
    return item


def _require(item: CoachMemory, *statuses: MemoryStatus) -> None:
    if item.status not in statuses:
        raise ConflictError(f"El elemento está en estado '{item.status.value}'.")


def _maybe_complete_intake(session: Session, item: CoachMemory) -> None:
    """La toma de contacto está hecha cuando no le queda nada pendiente de revisar."""
    if item.conversation_id is None:
        return
    conversation = session.get(CoachConversation, item.conversation_id)
    if (
        conversation is None
        or conversation.kind is not ConversationKind.INTAKE
        or conversation.intake_completed_at is not None
    ):
        return
    session.flush()
    pending = session.scalar(
        sa.select(sa.func.count()).where(
            CoachMemory.conversation_id == conversation.id,
            CoachMemory.status == MemoryStatus.PROPOSED,
        )
    )
    if not pending:
        conversation.intake_completed_at = datetime.now(UTC)
        conversation.updated_at = sa.func.now()


def confirm(
    session: Session,
    user_id: uuid.UUID,
    memory_id: uuid.UUID,
    *,
    content: str | None = None,
    kind: MemoryKind | None = None,
) -> CoachMemory:
    """Confirma una propuesta, con la corrección de la atleta si la hay. 409 si no está
    pendiente."""
    item = _get(session, user_id, memory_id)
    _require(item, MemoryStatus.PROPOSED)
    if content is not None:
        item.content = content.strip()
    if kind is not None:
        item.kind = kind
    item.status = MemoryStatus.CONFIRMED
    item.confirmed_at = datetime.now(UTC)
    item.updated_at = sa.func.now()
    _maybe_complete_intake(session, item)
    session.commit()
    session.refresh(item)
    return item


def reject(session: Session, user_id: uuid.UUID, memory_id: uuid.UUID) -> CoachMemory:
    item = _get(session, user_id, memory_id)
    _require(item, MemoryStatus.PROPOSED)
    item.status = MemoryStatus.REJECTED
    item.updated_at = sa.func.now()
    _maybe_complete_intake(session, item)
    session.commit()
    session.refresh(item)
    return item


def create(session: Session, user_id: uuid.UUID, kind: MemoryKind, content: str) -> CoachMemory:
    """La atleta añade un elemento directamente: queda confirmado."""
    item = CoachMemory(
        user_id=user_id,
        kind=kind,
        content=content.strip(),
        status=MemoryStatus.CONFIRMED,
        source=MemorySource.ATHLETE,
        confirmed_at=datetime.now(UTC),
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def update(
    session: Session,
    user_id: uuid.UUID,
    memory_id: uuid.UUID,
    *,
    content: str | None,
    kind: MemoryKind | None,
) -> CoachMemory:
    """Corrige un elemento confirmado. 409 si no está confirmado."""
    item = _get(session, user_id, memory_id)
    _require(item, MemoryStatus.CONFIRMED)
    if content is not None:
        item.content = content.strip()
    if kind is not None:
        item.kind = kind
    item.updated_at = sa.func.now()
    session.commit()
    session.refresh(item)
    return item


def delete(session: Session, user_id: uuid.UUID, memory_id: uuid.UUID) -> None:
    item = _get(session, user_id, memory_id)
    session.delete(item)
    session.commit()


# --- Resumen de la conversación --------------------------------------------------------------

SUMMARY_SYSTEM = (
    "Mantienes el resumen de una conversación entre una atleta y su entrenador digital. "
    "Recibes el resumen anterior (puede estar vacío) y mensajes nuevos. Devuelve sólo el "
    "resumen actualizado, en español y en un máximo de 200 palabras: hechos que la atleta ha "
    "contado, decisiones y temas pendientes. No inventes nada ni añadas cifras que no "
    "aparezcan en los mensajes."
)

VISIBLE_ROLES = (MessageRole.USER, MessageRole.ASSISTANT)


def visible_messages_after(
    session: Session, conversation_id: uuid.UUID, after_seq: int
) -> list[CoachMessage]:
    return list(
        session.scalars(
            sa.select(CoachMessage)
            .where(
                CoachMessage.conversation_id == conversation_id,
                CoachMessage.seq > after_seq,
                CoachMessage.role.in_(VISIBLE_ROLES),
            )
            .order_by(CoachMessage.seq)
        )
    )


def _transcript(messages: Sequence[CoachMessage]) -> str:
    names = {MessageRole.USER: "Atleta", MessageRole.ASSISTANT: "Coach"}
    return "\n".join(f"{names[m.role]}: {m.content}" for m in messages)


def refresh_summary(
    session: Session,
    settings: Settings,
    provider: LLMProvider,
    conversation: CoachConversation,
) -> list[LLMUsage]:
    """Incorpora al resumen los mensajes que han salido de la ventana (sin commit).

    Devuelve el uso de las llamadas hechas (ya registradas), por si el turno se deshace y hay
    que volver a registrarlas. Si el presupuesto está agotado o el LLM falla, no cambia el
    resumen: el contexto se queda con la ventana y el resumen anterior. Nunca registra el
    contenido de los mensajes.
    """
    pending = visible_messages_after(session, conversation.id, conversation.summary_through_seq)
    outside = pending[: max(len(pending) - settings.coach_history_messages, 0)]
    if len(outside) < settings.coach_summary_batch:
        return []
    if budget.budget_status(session, settings, conversation.user_id).exhausted:
        return []
    model = settings.coach_summary_model or settings.coach_model
    budget.price_for(settings, model)
    prompt = (
        f"Resumen anterior:\n{conversation.summary or '(vacío)'}\n\n"
        f"Mensajes nuevos:\n{_transcript(outside)}"
    )
    try:
        response = provider.complete(
            model=model,
            system=SUMMARY_SYSTEM,
            messages=[ChatMessage(role="user", text=prompt)],
            tools=(),
            max_tokens=600,
            effort="low",
        )
    except LLMError as exc:
        if exc.usage is not None:
            budget.record_call(
                session,
                settings,
                user_id=conversation.user_id,
                purpose=LlmCallPurpose.SUMMARY,
                provider=provider.name,
                model=model,
                usage=exc.usage,
                conversation_id=conversation.id,
            )
        logger.warning("No se ha podido actualizar el resumen de la conversación: %s", exc)
        return [] if exc.usage is None else [exc.usage]
    budget.record_call(
        session,
        settings,
        user_id=conversation.user_id,
        purpose=LlmCallPurpose.SUMMARY,
        provider=provider.name,
        model=model,
        usage=response.usage,
        conversation_id=conversation.id,
    )
    if response.text:
        conversation.summary = response.text
        conversation.summary_through_seq = outside[-1].seq
        conversation.updated_at = sa.func.now()
    return [response.usage]
