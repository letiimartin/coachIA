"""Coach v1 (#55): conversaciones con contexto, memoria confirmada y presupuesto.

Todo se filtra por la atleta del JWT: una conversación o un elemento de memoria de otra
atleta responde 404. La respuesta llega completa al final (sin streaming). En esta fase el
coach lee los datos y conversa; no cambia el plan.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession, LlmProviderDep, SettingsDep
from app.coach import budget, memory, orchestrator
from app.coach.orchestrator import TurnOutcome
from app.models.coach import MemoryStatus
from app.schemas.coach import (
    CoachReplyOut,
    CoachStatusOut,
    ConversationCreate,
    ConversationCreatedOut,
    ConversationOut,
    IntakeOut,
    MemoryConfirm,
    MemoryCreate,
    MemoryOut,
    MemoryPatch,
    MessageCreate,
    MessageOut,
    budget_out,
)
from app.schemas.common import error_responses
from app.services.athletes import ensure_athlete_profile

router = APIRouter(prefix="/coach", tags=["coach"])


def _reply_out(outcome: TurnOutcome) -> CoachReplyOut:
    return CoachReplyOut(
        user_message=None
        if outcome.user_message is None
        else MessageOut.model_validate(outcome.user_message),
        reply=MessageOut.model_validate(outcome.reply),
        memory_proposals=[MemoryOut.model_validate(m) for m in outcome.memory_proposals],
        budget=budget_out(outcome.budget),
    )


@router.get("/status", responses=error_responses())
def get_status(
    user: CurrentUser, db: DbSession, settings: SettingsDep, provider: LlmProviderDep
) -> CoachStatusOut:
    """Si el coach está disponible, el estado de la toma de contacto y el presupuesto del mes
    (con el aviso del 80 %)."""
    ensure_athlete_profile(db, user.id)
    intake = orchestrator.intake_status(db, user.id)
    return CoachStatusOut(
        available=provider is not None,
        model=settings.coach_model,
        intake=IntakeOut(
            state=intake.state,
            completed_at=intake.completed_at,
            conversation_id=intake.conversation_id,
        ),
        budget=budget_out(budget.budget_status(db, settings, user.id)),
    )


@router.post(
    "/conversations",
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(502, 503),
)
def create_conversation(
    user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
    provider: LlmProviderDep,
    body: ConversationCreate,
) -> ConversationCreatedOut:
    """Crea una conversación. La primera es la toma de contacto: el coach lee primero lo que
    ya sabe de la atleta y abre la conversación con sus primeras preguntas (`opening`).

    503 `coach_unavailable` si es una toma de contacto y no hay proveedor configurado; 502
    `coach_llm_error` si el LLM falla al abrirla (la conversación queda creada, vacía).
    """
    conversation, opening = orchestrator.create_conversation(
        db, settings, provider, user.id, body.kind
    )
    db.refresh(conversation)
    return ConversationCreatedOut(
        conversation=ConversationOut.model_validate(conversation),
        opening=None if opening is None else _reply_out(opening),
    )


@router.get("/conversations", responses=error_responses())
def list_conversations(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ConversationOut]:
    """Conversaciones de la atleta, de la más reciente a la más antigua."""
    return [
        ConversationOut.model_validate(c)
        for c in orchestrator.list_conversations(db, user.id, limit)
    ]


@router.get("/conversations/{conversation_id}", responses=error_responses(404))
def get_conversation(user: CurrentUser, db: DbSession, conversation_id: UUID) -> ConversationOut:
    return ConversationOut.model_validate(
        orchestrator.get_conversation(db, user.id, conversation_id)
    )


@router.get("/conversations/{conversation_id}/messages", responses=error_responses(404))
def list_messages(
    user: CurrentUser,
    db: DbSession,
    conversation_id: UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MessageOut]:
    """Los últimos `limit` mensajes de la atleta y del coach, en orden. Los resultados de
    herramientas se guardan para auditoría, pero no se devuelven."""
    return [
        MessageOut.model_validate(m)
        for m in orchestrator.list_messages(db, user.id, conversation_id, limit)
    ]


@router.post(
    "/conversations/{conversation_id}/messages",
    responses=error_responses(404, 502, 503),
)
def send_message(
    user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
    provider: LlmProviderDep,
    conversation_id: UUID,
    body: MessageCreate,
) -> CoachReplyOut:
    """Envía un mensaje y devuelve la respuesta completa del coach.

    - Si el mensaje habla de dolor torácico, mareo, desmayo o lesión aguda, la respuesta es
      fija, recomienda una valoración médica y no llama al LLM (`origin = safety_filter`).
    - Si el presupuesto del mes está agotado, la respuesta es fija (`origin = budget_limit`).
    - `memory_proposals`: lo que el coach propone recordar; la atleta lo confirma aparte.

    503 `coach_unavailable` si no hay proveedor (salvo el filtro de seguridad, que responde
    igual). 502 `coach_llm_error` si el LLM falla: el mensaje no se guarda y se puede
    reenviar.
    """
    outcome = orchestrator.send_message(
        db, settings, provider, user.id, conversation_id, body.content
    )
    return _reply_out(outcome)


# --- Memoria ---------------------------------------------------------------------------------


@router.get("/memory", responses=error_responses())
def list_memory(
    user: CurrentUser,
    db: DbSession,
    status_filter: Annotated[
        MemoryStatus | None,
        Query(alias="status", description="Por defecto, sólo la memoria confirmada."),
    ] = MemoryStatus.CONFIRMED,
) -> list[MemoryOut]:
    """Memoria del coach. Con `status=proposed`, lo que el coach ha propuesto y está pendiente
    de confirmar."""
    return [MemoryOut.model_validate(m) for m in memory.list_memory(db, user.id, status_filter)]


@router.post("/memory", status_code=status.HTTP_201_CREATED, responses=error_responses())
def create_memory(user: CurrentUser, db: DbSession, body: MemoryCreate) -> MemoryOut:
    """La atleta añade un objetivo o una preferencia: queda confirmado."""
    ensure_athlete_profile(db, user.id)
    return MemoryOut.model_validate(memory.create(db, user.id, body.kind, body.content))


@router.post("/memory/{memory_id}/confirm", responses=error_responses(404, 409))
def confirm_memory(
    user: CurrentUser, db: DbSession, memory_id: UUID, body: MemoryConfirm
) -> MemoryOut:
    """Confirma una propuesta del coach, con la corrección si se envía. 409 si no está
    pendiente. Cuando no queda nada pendiente en una toma de contacto, queda hecha."""
    return MemoryOut.model_validate(
        memory.confirm(db, user.id, memory_id, content=body.content, kind=body.kind)
    )


@router.post("/memory/{memory_id}/reject", responses=error_responses(404, 409))
def reject_memory(user: CurrentUser, db: DbSession, memory_id: UUID) -> MemoryOut:
    """Descarta una propuesta del coach. 409 si no está pendiente."""
    return MemoryOut.model_validate(memory.reject(db, user.id, memory_id))


@router.patch("/memory/{memory_id}", responses=error_responses(404, 409))
def update_memory(
    user: CurrentUser, db: DbSession, memory_id: UUID, body: MemoryPatch
) -> MemoryOut:
    """Corrige un elemento confirmado. 409 si no está confirmado."""
    return MemoryOut.model_validate(
        memory.update(db, user.id, memory_id, content=body.content, kind=body.kind)
    )


@router.delete(
    "/memory/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=error_responses(404),
)
def delete_memory(user: CurrentUser, db: DbSession, memory_id: UUID) -> None:
    """Borra un elemento de memoria: el coach deja de tenerlo en cuenta."""
    memory.delete(db, user.id, memory_id)
