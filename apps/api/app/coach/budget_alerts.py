"""Avisos de gasto del LLM a los desarrolladores (#61).

El gasto del LLM es cosa del equipo, no de la atleta: cuando el gasto del mes de una atleta cruza
el umbral de aviso (80 % por defecto) y el límite (100 %), se avisa a los desarrolladores **una
vez por umbral y mes**. La lógica está aquí; n8n sólo orquesta:

1. `pending_alerts` calcula los avisos pendientes: umbrales cruzados este mes (en la zona horaria
   de cada atleta) que aún no constan como enviados en `coach_budget_alerts`.
2. n8n envía cada aviso por email y confirma el envío con `mark_sent`, que lo registra.

El aviso sólo lleva cifras (mes, gasto, límite, llamadas y desglose por modelo) y el id de la
atleta: nunca contenido de las conversaciones ni datos de salud.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.coach.budget import BudgetState, budget_status, month_start
from app.core.config import Settings
from app.models import BudgetThreshold, CoachBudgetAlert, CoachLlmCall

# Basta con mirar las atletas con llamadas en este margen: cubre el mes en curso en cualquier zona.
_LOOKBACK = timedelta(days=33)
_CENT = Decimal("0.01")
_MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


@dataclass(frozen=True, slots=True)
class ModelUsage:
    model: str
    calls: int
    cost_eur: Decimal


@dataclass(frozen=True, slots=True)
class BudgetAlert:
    user_id: uuid.UUID
    month: date  # Primer día del mes.
    threshold: BudgetThreshold
    threshold_eur: Decimal  # Importe del umbral cruzado.
    spent_eur: Decimal
    limit_eur: Decimal
    calls: int
    by_model: tuple[ModelUsage, ...]

    @property
    def key(self) -> str:
        """Identifica el aviso para confirmar su envío."""
        return f"{self.user_id}:{self.month.isoformat()}:{self.threshold.value}"

    @property
    def percent(self) -> int:
        if self.limit_eur <= 0:
            return 100
        return int((self.spent_eur * 100 / self.limit_eur).to_integral_value(ROUND_HALF_UP))

    @property
    def subject(self) -> str:
        what = "límite alcanzado" if self.threshold is BudgetThreshold.LIMIT else "aviso"
        return (
            f"CoachIA · gasto del LLM al {self.percent} % ({what}) · "
            f"{_MONTHS[self.month.month - 1]} {self.month.year}"
        )

    @property
    def text(self) -> str:
        if self.threshold is BudgetThreshold.LIMIT:
            effect = (
                "Se ha llegado al límite: el coach ya no llama al LLM este mes y la atleta ve un "
                "mensaje neutro."
            )
        else:
            effect = (
                f"Se ha pasado el umbral de aviso ({_eur(self.threshold_eur)}). Al llegar al "
                "límite el coach dejará de llamar al LLM hasta el mes siguiente."
            )
        lines = [
            f"Mes: {self.month:%Y-%m}",
            f"Atleta: {self.user_id}",
            f"Gasto: {_eur(self.spent_eur)} de {_eur(self.limit_eur)} ({self.percent} %)",
            f"Llamadas al LLM: {self.calls}",
            "Por modelo:",
            *(f"  - {m.model}: {m.calls} llamadas, {_eur(m.cost_eur)}" for m in self.by_model),
            "",
            effect,
        ]
        return "\n".join(lines)


def _eur(value: Decimal) -> str:
    return f"{value.quantize(_CENT, rounding=ROUND_HALF_UP)} €"


def _crossed(state: BudgetState) -> list[BudgetThreshold]:
    if state is BudgetState.EXHAUSTED:
        return [BudgetThreshold.WARNING, BudgetThreshold.LIMIT]
    if state is BudgetState.WARNING:
        return [BudgetThreshold.WARNING]
    return []


def _usage_by_model(
    session: Session, user_id: uuid.UUID, start: datetime
) -> tuple[ModelUsage, ...]:
    rows = session.execute(
        sa.select(
            CoachLlmCall.model,
            sa.func.count(),
            sa.func.coalesce(sa.func.sum(CoachLlmCall.cost_eur), 0),
        )
        .where(CoachLlmCall.user_id == user_id, CoachLlmCall.created_at >= start)
        .group_by(CoachLlmCall.model)
        .order_by(sa.func.sum(CoachLlmCall.cost_eur).desc(), CoachLlmCall.model)
    ).all()
    return tuple(ModelUsage(model, int(calls), Decimal(cost)) for model, calls, cost in rows)


def pending_alerts(
    session: Session, settings: Settings, now: datetime | None = None
) -> list[BudgetAlert]:
    """Avisos de este mes aún no enviados, de todas las atletas."""
    now = now or datetime.now(UTC)
    user_ids = session.scalars(
        sa.select(CoachLlmCall.user_id)
        .where(CoachLlmCall.created_at >= now - _LOOKBACK)
        .distinct()
        .order_by(CoachLlmCall.user_id)
    ).all()
    alerts: list[BudgetAlert] = []
    for user_id in user_ids:
        status = budget_status(session, settings, user_id, now)
        crossed = _crossed(status.state)
        if not crossed:
            continue
        sent = set(
            session.scalars(
                sa.select(CoachBudgetAlert.threshold).where(
                    CoachBudgetAlert.user_id == user_id, CoachBudgetAlert.month == status.month
                )
            )
        )
        missing = [t for t in crossed if t not in sent]
        if not missing:
            continue
        by_model = _usage_by_model(session, user_id, month_start(session, user_id, now))
        for threshold in missing:
            alerts.append(
                BudgetAlert(
                    user_id=user_id,
                    month=status.month,
                    threshold=threshold,
                    threshold_eur=status.limit_eur
                    if threshold is BudgetThreshold.LIMIT
                    else status.warning_eur,
                    spent_eur=status.spent_eur,
                    limit_eur=status.limit_eur,
                    calls=sum(m.calls for m in by_model),
                    by_model=by_model,
                )
            )
    return alerts


@dataclass(frozen=True, slots=True)
class MarkSentOutcome:
    recorded: int  # Avisos registrados como enviados ahora.
    ignored: int  # Claves que no son avisos pendientes (ya registrados, de otro mes o inválidas).


def mark_sent(
    session: Session, settings: Settings, keys: list[str], now: datetime | None = None
) -> MarkSentOutcome:
    """Registra como enviados los avisos pendientes con esas claves (con commit).

    Sólo se registran avisos pendientes de verdad: una clave inventada, repetida o de un umbral
    que aún no se ha cruzado se ignora, para no silenciar un aviso futuro.
    """
    pending = {alert.key: alert for alert in pending_alerts(session, settings, now)}
    recorded = 0
    for key in dict.fromkeys(keys):
        alert = pending.get(key)
        if alert is None:
            continue
        inserted = session.scalar(
            insert(CoachBudgetAlert)
            .values(
                user_id=alert.user_id,
                month=alert.month,
                threshold=alert.threshold,
                spent_eur=alert.spent_eur,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "month", "threshold"])
            .returning(CoachBudgetAlert.id)
        )
        recorded += inserted is not None
    session.commit()
    return MarkSentOutcome(recorded=recorded, ignored=len(keys) - recorded)
