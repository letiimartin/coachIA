"""Coste de las llamadas al LLM y presupuesto mensual del coach.

El límite está en el código: antes de cada llamada se suma el coste de todas las llamadas del
mes (`coach_llm_calls`: conversación, resúmenes y, más adelante, el planificador). Al llegar al
80 % hay aviso; al 100 % el coach responde con un mensaje fijo y no llama al LLM.

El coste se calcula con los precios oficiales configurados (USD por millón de tokens) y se pasa
a euros con `coach_usd_to_eur`. El mes es el natural en la zona horaria de la atleta.
"""

import enum
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.coach.llm.base import LLMUsage
from app.core.config import ModelPrice, Settings
from app.core.errors import ServiceUnavailableError
from app.models import CoachLlmCall, LlmCallPurpose
from app.services.athletes import athlete_timezone

_MTOK = Decimal(1_000_000)
_MICRO = Decimal("0.000001")

BUDGET_EXHAUSTED_REPLY = (
    "Este mes ya se ha usado todo el presupuesto del coach, así que ahora no puedo responder "
    "con el modelo de lenguaje. Tus datos, el plan y el calendario siguen disponibles en la "
    "app, y el coach vuelve a estar activo el día 1 del mes que viene."
)


class BudgetState(enum.StrEnum):
    OK = "ok"
    WARNING = "warning"  # Se ha pasado el umbral de aviso (80 % por defecto).
    EXHAUSTED = "exhausted"  # Se ha llegado al límite: no se llama al LLM.


@dataclass(frozen=True, slots=True)
class BudgetStatus:
    month: date  # Primer día del mes.
    spent_eur: Decimal
    limit_eur: Decimal
    warning_eur: Decimal
    state: BudgetState

    @property
    def exhausted(self) -> bool:
        return self.state is BudgetState.EXHAUSTED


def price_for(settings: Settings, model: str) -> ModelPrice:
    """Precio del modelo. Sin precio no se puede controlar el presupuesto: no se llama."""
    price = settings.coach_llm_prices.get(model)
    if price is None:
        raise ServiceUnavailableError(f"No hay precio configurado para el modelo {model}.")
    return price


def call_cost_usd(price: ModelPrice, usage: LLMUsage) -> Decimal:
    multiplier = (
        price.long_context_multiplier
        if price.long_context_over_tokens is not None
        and usage.prompt_tokens > price.long_context_over_tokens
        else Decimal(1)
    )
    total = (
        usage.input_tokens * price.input
        + usage.output_tokens * price.output
        + usage.cache_write_tokens * price.cache_write
        + usage.cache_read_tokens * price.cache_read
    )
    return (total * multiplier / _MTOK).quantize(_MICRO, rounding=ROUND_HALF_UP)


def to_eur(settings: Settings, usd: Decimal) -> Decimal:
    return (usd * settings.coach_usd_to_eur).quantize(_MICRO, rounding=ROUND_HALF_UP)


def month_start(session: Session, user_id: uuid.UUID, now: datetime | None = None) -> datetime:
    tz = ZoneInfo(athlete_timezone(session, user_id))
    local = (now or datetime.now(tz)).astimezone(tz)
    return datetime.combine(local.date().replace(day=1), time.min, tzinfo=tz)


def budget_status(
    session: Session, settings: Settings, user_id: uuid.UUID, now: datetime | None = None
) -> BudgetStatus:
    start = month_start(session, user_id, now)
    spent = session.scalar(
        sa.select(sa.func.coalesce(sa.func.sum(CoachLlmCall.cost_eur), 0)).where(
            CoachLlmCall.user_id == user_id, CoachLlmCall.created_at >= start
        )
    )
    spent = Decimal(spent or 0)
    limit = settings.coach_monthly_budget_eur
    warning = (limit * settings.coach_budget_warning_ratio).quantize(Decimal("0.01"))
    if spent >= limit:
        state = BudgetState.EXHAUSTED
    elif spent >= warning:
        state = BudgetState.WARNING
    else:
        state = BudgetState.OK
    return BudgetStatus(start.date(), spent, limit, warning, state)


def record_call(
    session: Session,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    purpose: LlmCallPurpose,
    provider: str,
    model: str,
    usage: LLMUsage,
    conversation_id: uuid.UUID | None,
) -> CoachLlmCall:
    """Registra una llamada (sin commit) con su coste en USD y en EUR."""
    usd = call_cost_usd(price_for(settings, model), usage)
    call = CoachLlmCall(
        user_id=user_id,
        conversation_id=conversation_id,
        purpose=purpose,
        provider=provider,
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read_tokens=usage.cache_read_tokens,
        cache_write_tokens=usage.cache_write_tokens,
        cost_usd=usd,
        cost_eur=to_eur(settings, usd),
    )
    session.add(call)
    session.flush()
    return call
