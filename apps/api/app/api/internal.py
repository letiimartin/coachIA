"""Endpoints internos para automatizaciones (n8n). Protegidos con la cabecera X-Internal-API-Key."""

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import (
    DbSession,
    SettingsDep,
    TokenCipherDep,
    WahooClientDep,
    require_internal_api_key,
)
from app.coach import budget_alerts
from app.integrations.wahoo import sync as wahoo_sync

router = APIRouter(
    prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal_api_key)]
)


class PingResponse(BaseModel):
    status: Literal["ok"]


@router.get("/ping")
def ping() -> PingResponse:
    """Permite a n8n comprobar que la API responde y que su clave es correcta."""
    return PingResponse(status="ok")


class InternalSyncOut(BaseModel):
    """Resultado agregado de sincronizar todas las integraciones activas."""

    integrations: int
    succeeded: int
    failed: int
    rate_limited: bool
    created: int
    updated: int
    unchanged: int


@router.post("/sync/wahoo")
def sync_wahoo_all(
    db: DbSession, cipher: TokenCipherDep, client: WahooClientDep
) -> InternalSyncOut:
    """Sincroniza las actividades de todas las integraciones de Wahoo activas (para n8n).

    Si Wahoo aplica el límite de peticiones se detiene (`rate_limited`): el resto de usuarios se
    sincroniza en la siguiente ejecución, empezando por los que llevan más tiempo sin hacerlo.
    """
    outcome = wahoo_sync.sync_all(db, cipher, client)
    return InternalSyncOut(
        integrations=outcome.integrations,
        succeeded=outcome.succeeded,
        failed=outcome.failed,
        rate_limited=outcome.rate_limited,
        created=outcome.totals.created,
        updated=outcome.totals.updated,
        unchanged=outcome.totals.unchanged,
    )


class ModelUsageOut(BaseModel):
    model: str
    calls: int
    cost_eur: float


class BudgetAlertOut(BaseModel):
    """Aviso de gasto del LLM para los desarrolladores. Sólo cifras: nunca contenido de las
    conversaciones ni datos de salud. `subject` y `text` son el email ya redactado."""

    key: str = Field(description="Identifica el aviso; se envía a `/sent` tras mandarlo.")
    user_id: UUID
    month: date = Field(description="Primer día del mes (zona horaria de la atleta).")
    threshold: Literal["warning", "limit"] = Field(
        description="`warning`: umbral de aviso (80 % por defecto). `limit`: 100 %."
    )
    threshold_eur: float
    spent_eur: float
    limit_eur: float
    percent: int
    calls: int
    by_model: list[ModelUsageOut]
    subject: str
    text: str


class BudgetAlertsOut(BaseModel):
    alerts: list[BudgetAlertOut]


class BudgetAlertsSent(BaseModel):
    keys: list[str] = Field(min_length=1, max_length=100)


class BudgetAlertsSentOut(BaseModel):
    recorded: int
    ignored: int


def _alert_out(alert: budget_alerts.BudgetAlert) -> BudgetAlertOut:
    return BudgetAlertOut(
        key=alert.key,
        user_id=alert.user_id,
        month=alert.month,
        threshold=alert.threshold.value,
        threshold_eur=float(alert.threshold_eur),
        spent_eur=round(float(alert.spent_eur), 6),
        limit_eur=float(alert.limit_eur),
        percent=alert.percent,
        calls=alert.calls,
        by_model=[
            ModelUsageOut(model=m.model, calls=m.calls, cost_eur=round(float(m.cost_eur), 6))
            for m in alert.by_model
        ],
        subject=alert.subject,
        text=alert.text,
    )


@router.get("/coach/budget-alerts")
def list_budget_alerts(db: DbSession, settings: SettingsDep) -> BudgetAlertsOut:
    """Avisos de gasto del LLM pendientes (para n8n): umbrales del 80 % y del 100 % del límite
    mensual cruzados este mes y aún no enviados. Uno por atleta, mes y umbral.

    n8n envía cada aviso por email y después confirma el envío con `POST .../sent`; hasta
    entonces el aviso sigue apareciendo aquí.
    """
    return BudgetAlertsOut(
        alerts=[_alert_out(a) for a in budget_alerts.pending_alerts(db, settings)]
    )


@router.post("/coach/budget-alerts/sent")
def mark_budget_alerts_sent(
    db: DbSession, settings: SettingsDep, body: BudgetAlertsSent
) -> BudgetAlertsSentOut:
    """Registra como enviados los avisos con esas claves, para no repetirlos.

    Sólo se registran avisos pendientes: las claves ya registradas, de otro mes o de un umbral
    no cruzado se ignoran (`ignored`).
    """
    outcome = budget_alerts.mark_sent(db, settings, body.keys)
    return BudgetAlertsSentOut(recorded=outcome.recorded, ignored=outcome.ignored)
