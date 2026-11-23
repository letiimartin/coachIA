"""Schemas del coach (#55): conversaciones, mensajes, memoria confirmada y presupuesto."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.coach import (
    ConversationChannel,
    ConversationKind,
    MemoryKind,
    MemorySource,
    MemoryStatus,
    MessageOrigin,
    MessageRole,
)

if TYPE_CHECKING:
    from app.coach.budget import BudgetStatus

MemoryContent = Annotated[str, Field(min_length=1, max_length=1000)]

# --- Presupuesto e intake --------------------------------------------------------------------


class BudgetOut(BaseModel):
    """Presupuesto mensual del LLM (todas las llamadas del mes, en euros).

    - `ok`: por debajo del aviso.
    - `warning`: se ha pasado el aviso (80 % por defecto). El aviso es para los
      desarrolladores (#61, por n8n): la app no lo muestra a la atleta.
    - `exhausted`: se ha llegado al límite; el coach responde con un mensaje fijo sin llamar
      al LLM hasta el mes siguiente.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "month": "2026-11-01",
                    "spent_eur": 3.31,
                    "limit_eur": 4.0,
                    "warning_eur": 3.2,
                    "state": "warning",
                }
            ]
        }
    )

    month: date = Field(description="Primer día del mes (zona horaria de la atleta).")
    spent_eur: float
    limit_eur: float
    warning_eur: float
    state: Literal["ok", "warning", "exhausted"]


class IntakeOut(BaseModel):
    """Toma de contacto: `not_started`, `in_progress` (la última sin terminar, también si se
    repite) o `completed`. `completed_at`: la última vez que se terminó."""

    state: Literal["not_started", "in_progress", "completed"]
    completed_at: datetime | None
    conversation_id: UUID | None = Field(description="La última toma de contacto.")


class CoachStatusOut(BaseModel):
    available: bool = Field(description="Hay un proveedor de LLM configurado.")
    model: str = Field(description="Modelo que conversa.")
    intake: IntakeOut
    budget: BudgetOut


# --- Conversaciones y mensajes ---------------------------------------------------------------


class ConversationCreate(BaseModel):
    """Sin `kind`, la conversación es una toma de contacto si aún no se ha hecho ninguna y,
    si no, una conversación normal. `intake` repite la toma de contacto."""

    model_config = ConfigDict(extra="forbid")

    kind: ConversationKind | None = None


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel: ConversationChannel
    kind: ConversationKind
    title: str | None
    summary: str | None = Field(
        description="Resumen de los mensajes antiguos (lo mantiene el código)."
    )
    last_message_at: datetime | None
    intake_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    """Mensaje de la atleta (`user`) o del coach (`assistant`).

    `origin` (sólo en `assistant`): `llm`, `safety_filter` (respuesta fija del filtro de
    seguridad, sin LLM) o `budget_limit` (respuesta fija por presupuesto agotado).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seq: int
    role: MessageRole
    origin: MessageOrigin | None
    content: str
    model: str | None
    tokens_in: int | None
    tokens_out: int | None
    cost_eur: float | None
    created_at: datetime


class MessageCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"content": "¿Qué hago hoy? Tengo una hora."}]},
    )

    content: Annotated[str, Field(min_length=1, max_length=4000)]

    @model_validator(mode="after")
    def _not_blank(self) -> "MessageCreate":
        if not self.content.strip():
            raise ValueError("el mensaje no puede estar vacío")
        return self


class MemoryOut(BaseModel):
    """Elemento de memoria. `source`: `coach` (propuesto por el coach) o `athlete` (añadido por
    ella). `status`: `proposed` (pendiente de confirmar), `confirmed`, `rejected` o
    `superseded` (el coach lo sustituyó por otra propuesta). El origen es la conversación y
    el mensaje del coach que lo propuso; `confirmed_at`, cuándo lo confirmó la atleta."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: MemoryKind
    content: str
    status: MemoryStatus
    source: MemorySource
    conversation_id: UUID | None
    source_message_id: UUID | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CoachReplyOut(BaseModel):
    """Resultado de un mensaje: el de la atleta, la respuesta completa del coach (sin
    streaming), lo que el coach propone recordar (pendiente de confirmar) y el presupuesto."""

    user_message: MessageOut | None = Field(
        description="Null cuando el coach abre la conversación."
    )
    reply: MessageOut
    memory_proposals: list[MemoryOut]
    budget: BudgetOut


class ConversationCreatedOut(BaseModel):
    conversation: ConversationOut
    opening: CoachReplyOut | None = Field(
        description="En la toma de contacto, el primer mensaje del coach. Null en las demás."
    )


# --- Memoria ---------------------------------------------------------------------------------


class MemoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: MemoryKind
    content: MemoryContent


class MemoryConfirm(BaseModel):
    """Confirma una propuesta, opcionalmente corregida."""

    model_config = ConfigDict(extra="forbid")

    kind: MemoryKind | None = None
    content: MemoryContent | None = None


class MemoryPatch(BaseModel):
    """Corrige un elemento confirmado (sólo los campos enviados)."""

    model_config = ConfigDict(extra="forbid")

    kind: MemoryKind | None = None
    content: MemoryContent | None = None

    @model_validator(mode="after")
    def _something(self) -> "MemoryPatch":
        if self.kind is None and self.content is None:
            raise ValueError("hay que enviar 'kind' o 'content'")
        return self


def budget_out(status: "BudgetStatus") -> BudgetOut:
    return BudgetOut(
        month=status.month,
        spent_eur=round(float(status.spent_eur), 6),
        limit_eur=float(status.limit_eur),
        warning_eur=float(status.warning_eur),
        state=status.state.value,
    )
