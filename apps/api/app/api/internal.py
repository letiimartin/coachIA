"""Endpoints internos para automatizaciones (n8n). Protegidos con la cabecera X-Internal-API-Key."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import DbSession, TokenCipherDep, WahooClientDep, require_internal_api_key
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
