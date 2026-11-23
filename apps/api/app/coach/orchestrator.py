"""Flujo completo de un mensaje al coach, con persistencia.

1. Filtro de seguridad determinista: si salta, respuesta fija sin llamar al LLM.
2. Presupuesto: si está agotado, respuesta fija sin llamar al LLM.
3. Resumen: si han salido bastantes mensajes de la ventana, se actualiza (cuenta en el mes).
4. Contexto: un primer mensaje con la fecha, la memoria confirmada y el resumen; después los
   últimos N mensajes. El prompt de sistema y las herramientas son estables (caché).
5. Respuesta con herramientas (`engine.run_turn`), registrando el coste de cada llamada.

Se guarda todo: el mensaje de la atleta, los resultados de las herramientas (`tool`) y la
respuesta con su modelo, tokens y coste. Nunca se registra el contenido de los mensajes en los
logs.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.coach import budget, memory, prompts
from app.coach.data import DbCoachData
from app.coach.engine import TurnResult, run_turn
from app.coach.llm.base import ChatMessage, LLMError, LLMProvider, LLMUsage
from app.coach.safety import SAFETY_REPLY, check_message
from app.coach.tools import TOOL_SPECS
from app.core.config import Settings
from app.core.errors import BadGatewayError, NotFoundError, ServiceUnavailableError
from app.models import (
    CoachConversation,
    CoachLlmCall,
    CoachMemory,
    CoachMessage,
    ConversationKind,
    LlmCallPurpose,
    MemoryStatus,
    MessageOrigin,
    MessageRole,
)
from app.services.athletes import athlete_timezone, ensure_athlete_profile

logger = logging.getLogger(__name__)

INTAKE_TITLE = "Toma de contacto"
INTAKE_OPENING = (
    "(Sistema: la atleta acaba de abrir la toma de contacto. Empieza tú, siguiendo las "
    "instrucciones de la toma de contacto.)"
)
_TITLE_LENGTH = 60
_WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


class CoachUnavailableError(ServiceUnavailableError):
    code = "coach_unavailable"
    message = "El coach no está configurado (falta la clave del proveedor de LLM)."


class CoachLlmError(BadGatewayError):
    code = "coach_llm_error"
    message = "El modelo de lenguaje no ha respondido. Inténtalo de nuevo en un momento."


@dataclass
class TurnOutcome:
    user_message: CoachMessage | None
    reply: CoachMessage
    budget: budget.BudgetStatus
    memory_proposals: list[CoachMemory] = field(default_factory=list)


# --- Conversaciones --------------------------------------------------------------------------


def get_conversation(
    session: Session, user_id: uuid.UUID, conversation_id: uuid.UUID, *, for_update: bool = False
) -> CoachConversation:
    query = sa.select(CoachConversation).where(
        CoachConversation.id == conversation_id, CoachConversation.user_id == user_id
    )
    if for_update:
        query = query.with_for_update()
    conversation = session.scalar(query)
    if conversation is None:
        raise NotFoundError("Conversación no encontrada.")
    return conversation


def list_conversations(session: Session, user_id: uuid.UUID, limit: int) -> list[CoachConversation]:
    return list(
        session.scalars(
            sa.select(CoachConversation)
            .where(CoachConversation.user_id == user_id)
            .order_by(
                sa.func.coalesce(
                    CoachConversation.last_message_at, CoachConversation.created_at
                ).desc(),
                CoachConversation.id,
            )
            .limit(limit)
        )
    )


def list_messages(
    session: Session, user_id: uuid.UUID, conversation_id: uuid.UUID, limit: int
) -> list[CoachMessage]:
    """Los últimos `limit` mensajes de la atleta y del coach, del más antiguo al más nuevo."""
    get_conversation(session, user_id, conversation_id)
    rows = session.scalars(
        sa.select(CoachMessage)
        .where(
            CoachMessage.conversation_id == conversation_id,
            CoachMessage.role.in_(memory.VISIBLE_ROLES),
        )
        .order_by(CoachMessage.seq.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))


def intake_done(session: Session, user_id: uuid.UUID) -> bool:
    return bool(
        session.scalar(
            sa.select(sa.literal(True)).where(
                CoachConversation.user_id == user_id,
                CoachConversation.intake_completed_at.is_not(None),
            )
        )
    )


@dataclass(frozen=True, slots=True)
class IntakeStatus:
    state: Literal["not_started", "in_progress", "completed"]
    completed_at: datetime | None
    conversation_id: uuid.UUID | None  # La última toma de contacto.


def intake_status(session: Session, user_id: uuid.UUID) -> IntakeStatus:
    latest = session.scalar(
        sa.select(CoachConversation)
        .where(
            CoachConversation.user_id == user_id,
            CoachConversation.kind == ConversationKind.INTAKE,
        )
        .order_by(CoachConversation.created_at.desc(), CoachConversation.id)
        .limit(1)
    )
    completed_at = session.scalar(
        sa.select(sa.func.max(CoachConversation.intake_completed_at)).where(
            CoachConversation.user_id == user_id
        )
    )
    if latest is None:
        return IntakeStatus("not_started", None, None)
    # Una toma de contacto repetida y sin terminar cuenta como en curso.
    if latest.intake_completed_at is not None:
        return IntakeStatus("completed", completed_at, latest.id)
    return IntakeStatus("in_progress", completed_at, latest.id)


def create_conversation(
    session: Session,
    settings: Settings,
    provider: LLMProvider | None,
    user_id: uuid.UUID,
    kind: ConversationKind | None,
) -> tuple[CoachConversation, TurnOutcome | None]:
    """Crea una conversación. Sin `kind`, es una toma de contacto si aún no se ha hecho ninguna.

    En la toma de contacto el coach abre la conversación (llama al LLM, salvo que el
    presupuesto esté agotado): lee los datos y hace las primeras preguntas.
    """
    ensure_athlete_profile(session, user_id)
    if kind is None:
        kind = ConversationKind.CHAT if intake_done(session, user_id) else ConversationKind.INTAKE
    if kind is ConversationKind.INTAKE and provider is None:
        raise CoachUnavailableError()
    conversation = CoachConversation(
        user_id=user_id,
        kind=kind,
        title=INTAKE_TITLE if kind is ConversationKind.INTAKE else None,
    )
    session.add(conversation)
    session.commit()
    if kind is not ConversationKind.INTAKE or provider is None:
        return conversation, None
    outcome = _respond(session, settings, provider, conversation, None)
    return conversation, outcome


# --- Mensajes --------------------------------------------------------------------------------


def _next_seq(session: Session, conversation_id: uuid.UUID) -> int:
    current = session.scalar(
        sa.select(sa.func.coalesce(sa.func.max(CoachMessage.seq), 0)).where(
            CoachMessage.conversation_id == conversation_id
        )
    )
    return int(current or 0) + 1


def _add_message(
    session: Session, conversation: CoachConversation, **values: object
) -> CoachMessage:
    message = CoachMessage(
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        seq=_next_seq(session, conversation.id),
        **values,
    )
    session.add(message)
    session.flush()
    return message


def _touch(conversation: CoachConversation, first_user_text: str | None) -> None:
    conversation.last_message_at = datetime.now(UTC)
    conversation.updated_at = sa.func.now()
    if conversation.title is None and first_user_text:
        title = " ".join(first_user_text.split())
        conversation.title = (
            title if len(title) <= _TITLE_LENGTH else title[: _TITLE_LENGTH - 1].rstrip() + "…"
        )


def _fixed_reply(
    session: Session,
    settings: Settings,
    conversation: CoachConversation,
    user_message: CoachMessage | None,
    text: str,
    origin: MessageOrigin,
) -> TurnOutcome:
    reply = _add_message(
        session, conversation, role=MessageRole.ASSISTANT, origin=origin, content=text
    )
    _touch(conversation, None if user_message is None else user_message.content)
    session.commit()
    status = budget.budget_status(session, settings, conversation.user_id)
    return TurnOutcome(user_message, reply, status)


def send_message(
    session: Session,
    settings: Settings,
    provider: LLMProvider | None,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    content: str,
) -> TurnOutcome:
    safety = check_message(content)
    conversation = get_conversation(session, user_id, conversation_id, for_update=True)
    if safety.triggered:
        user_message = _add_message(session, conversation, role=MessageRole.USER, content=content)
        logger.info("Filtro de seguridad del coach: %s", ",".join(f.value for f in safety.flags))
        return _fixed_reply(
            session, settings, conversation, user_message, SAFETY_REPLY, MessageOrigin.SAFETY_FILTER
        )
    if provider is None:
        session.rollback()
        raise CoachUnavailableError()
    if budget.budget_status(session, settings, user_id).exhausted:
        user_message = _add_message(session, conversation, role=MessageRole.USER, content=content)
        return _fixed_reply(
            session,
            settings,
            conversation,
            user_message,
            budget.BUDGET_EXHAUSTED_REPLY,
            MessageOrigin.BUDGET_LIMIT,
        )
    budget.price_for(settings, settings.coach_model)
    user_message = _add_message(session, conversation, role=MessageRole.USER, content=content)
    return _respond(session, settings, provider, conversation, user_message)


def _context_message(
    session: Session, conversation: CoachConversation, today_label: str
) -> ChatMessage:
    confirmed = memory.confirmed_memory(session, conversation.user_id)
    lines = [
        "[Contexto del sistema; no es un mensaje de la atleta]",
        f"- Hoy: {today_label}.",
        "- Conversación: "
        + ("toma de contacto." if conversation.kind is ConversationKind.INTAKE else "normal."),
        "- Toma de contacto: "
        + ("hecha." if intake_done(session, conversation.user_id) else "pendiente."),
    ]
    if confirmed:
        lines.append("- Memoria confirmada:")
        lines.extend(f"  - ({m.kind.value}) {m.content}" for m in confirmed)
    else:
        lines.append("- Memoria confirmada: ninguna todavía.")
    if conversation.summary:
        lines.append(
            f"- Resumen de los mensajes anteriores de esta conversación:\n{conversation.summary}"
        )
    return ChatMessage(role="user", text="\n".join(lines))


def _respond(
    session: Session,
    settings: Settings,
    provider: LLMProvider,
    conversation: CoachConversation,
    user_message: CoachMessage | None,
) -> TurnOutcome:
    """Genera la respuesta del coach con el LLM y la guarda. Sin `user_message`, abre la
    toma de contacto."""
    user_id = conversation.user_id
    model = settings.coach_model
    budget.price_for(settings, model)
    tz = ZoneInfo(athlete_timezone(session, user_id))
    now = datetime.now(tz)
    today = now.date()

    summary_usages = memory.refresh_summary(session, settings, provider, conversation)
    history = memory.visible_messages_after(
        session, conversation.id, conversation.summary_through_seq
    )[-settings.coach_history_messages :]
    messages = [
        _context_message(
            session, conversation, f"{today.isoformat()} ({_WEEKDAYS[today.weekday()]}), {tz.key}"
        ),
        *(
            ChatMessage(role="user" if m.role is MessageRole.USER else "assistant", text=m.content)
            for m in history
        ),
    ]
    if user_message is None:
        messages.append(ChatMessage(role="user", text=INTAKE_OPENING))

    data = DbCoachData(
        session,
        user_id,
        today=today,
        conversation_id=conversation.id,
        user_message_id=None if user_message is None else user_message.id,
    )
    calls: list[CoachLlmCall] = []
    usages: list[LLMUsage] = []

    def on_call(usage: LLMUsage) -> None:
        usages.append(usage)
        calls.append(
            budget.record_call(
                session,
                settings,
                user_id=user_id,
                purpose=LlmCallPurpose.CHAT,
                provider=provider.name,
                model=model,
                usage=usage,
                conversation_id=conversation.id,
            )
        )

    def has_budget() -> bool:
        return not budget.budget_status(session, settings, user_id).exhausted

    try:
        turn = run_turn(
            provider=provider,
            model=model,
            system=prompts.system_prompt(intake=conversation.kind is ConversationKind.INTAKE),
            messages=messages,
            tools=TOOL_SPECS,
            data=data,
            max_rounds=settings.coach_max_tool_rounds,
            max_tokens=settings.coach_max_output_tokens,
            effort=settings.coach_effort,
            on_call=on_call,
            has_budget=has_budget,
        )
    except LLMError as exc:
        _record_failure(
            session, settings, provider, conversation, model, usages, summary_usages, exc
        )
        raise CoachLlmError() from exc
    return _save_turn(session, settings, conversation, user_message, turn, calls, data)


def _record_failure(
    session: Session,
    settings: Settings,
    provider: LLMProvider,
    conversation: CoachConversation,
    model: str,
    usages: list[LLMUsage],
    summary_usages: list[LLMUsage],
    exc: LLMError,
) -> None:
    """Deshace el turno (el mensaje de la atleta no se guarda) pero conserva el coste."""
    session.rollback()
    if exc.usage is not None:
        usages = [*usages, exc.usage]
    summary_model = settings.coach_summary_model or settings.coach_model
    for purpose, call_model, usage in [
        *((LlmCallPurpose.SUMMARY, summary_model, u) for u in summary_usages),
        *((LlmCallPurpose.CHAT, model, u) for u in usages),
    ]:
        budget.record_call(
            session,
            settings,
            user_id=conversation.user_id,
            purpose=purpose,
            provider=provider.name,
            model=call_model,
            usage=usage,
            conversation_id=conversation.id,
        )
    session.commit()
    logger.warning("El LLM del coach ha fallado: %s", exc)


def _save_turn(
    session: Session,
    settings: Settings,
    conversation: CoachConversation,
    user_message: CoachMessage | None,
    turn: TurnResult,
    calls: list[CoachLlmCall],
    data: DbCoachData,
) -> TurnOutcome:
    for step in turn.steps:
        _add_message(
            session,
            conversation,
            role=MessageRole.TOOL,
            origin=MessageOrigin.TOOL,
            content=step.result.content,
            tool_calls=[
                {
                    "id": step.call.id,
                    "name": step.call.name,
                    "input": step.call.input,
                    "is_error": step.result.is_error,
                }
            ],
        )
    stopped = turn.stopped_by_budget
    reply = _add_message(
        session,
        conversation,
        role=MessageRole.ASSISTANT,
        origin=MessageOrigin.BUDGET_LIMIT if stopped else MessageOrigin.LLM,
        content=budget.BUDGET_EXHAUSTED_REPLY if stopped else turn.text,
        tool_calls=[
            {"name": s.call.name, "input": s.call.input, "is_error": s.result.is_error}
            for s in turn.steps
        ]
        or None,
        model=turn.model,
        tokens_in=turn.usage.prompt_tokens,
        tokens_out=turn.usage.output_tokens,
        cost_eur=sum((c.cost_eur for c in calls), Decimal(0)),
    )
    for call in calls:
        call.message_id = reply.id
    memory.attach_source_message(session, data.proposed_memory_ids, reply.id)
    _touch(conversation, None if user_message is None else user_message.content)
    session.commit()
    proposals = (
        list(
            session.scalars(
                sa.select(CoachMemory).where(
                    CoachMemory.id.in_(data.proposed_memory_ids),
                    CoachMemory.status == MemoryStatus.PROPOSED,
                )
            )
        )
        if data.proposed_memory_ids
        else []
    )
    logger.info(
        "Respuesta del coach: modelo=%s llamadas=%d tokens_in=%d tokens_out=%d coste_eur=%s",
        turn.model,
        turn.llm_calls,
        turn.usage.prompt_tokens,
        turn.usage.output_tokens,
        reply.cost_eur,
    )
    status = budget.budget_status(session, settings, conversation.user_id)
    return TurnOutcome(user_message, reply, status, proposals)
