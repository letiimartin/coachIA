"""Integraciones del usuario autenticado (estado, inicio de conexión y desconexión)."""

from datetime import datetime

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, StateSignerDep, TokenCipherDep, WahooClientDep
from app.core.errors import (
    BadGatewayError,
    ConflictError,
    NotFoundError,
    TooManyRequestsError,
)
from app.core.oauth_state import OAuthState, Platform
from app.integrations.wahoo import service as wahoo_service
from app.integrations.wahoo import sync as wahoo_sync
from app.integrations.wahoo.client import (
    WahooApiError,
    WahooRateLimitError,
    WahooUnauthorizedError,
)
from app.models import Integration, IntegrationStatus, Provider

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationOut(BaseModel):
    """Estado de una integración. Nunca incluye tokens."""

    provider: Provider
    status: IntegrationStatus
    scopes: list[str]
    connected_at: datetime
    token_expires_at: datetime | None
    last_sync_at: datetime | None
    last_error: str | None


class AuthorizeUrlOut(BaseModel):
    authorize_url: str


class SyncOut(BaseModel):
    """Resultado de una sincronización: actividades creadas, actualizadas y sin cambios."""

    created: int
    updated: int
    unchanged: int


@router.get("")
def list_integrations(user: CurrentUser, db: DbSession) -> list[IntegrationOut]:
    rows = db.scalars(
        select(Integration).where(Integration.user_id == user.id).order_by(Integration.provider)
    )
    return [
        IntegrationOut(
            provider=row.provider,
            status=row.status,
            scopes=row.scopes,
            connected_at=row.created_at,
            token_expires_at=row.token_expires_at,
            last_sync_at=row.last_sync_at,
            last_error=row.last_error,
        )
        for row in rows
    ]


@router.get("/wahoo/authorize-url")
def wahoo_authorize_url(
    user: CurrentUser,
    signer: StateSignerDep,
    client: WahooClientDep,
    platform: Platform = "mobile",
) -> AuthorizeUrlOut:
    """URL a la que la app debe enviar al usuario para autorizar CoachIA en Wahoo."""
    state = signer.sign(OAuthState(user_id=user.id, provider=Provider.WAHOO, platform=platform))
    return AuthorizeUrlOut(authorize_url=client.authorize_url(state))


@router.delete("/wahoo", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_wahoo(user: CurrentUser, db: DbSession) -> Response:
    if not wahoo_service.disconnect(db, user.id):
        raise NotFoundError("No hay ninguna cuenta de Wahoo conectada.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/wahoo/sync")
def sync_wahoo(
    user: CurrentUser, db: DbSession, cipher: TokenCipherDep, client: WahooClientDep
) -> SyncOut:
    """Importa las actividades realizadas en Wahoo. Es idempotente: se puede repetir sin riesgo."""
    try:
        result = wahoo_sync.sync_user(db, cipher, client, user.id)
    except (wahoo_service.WahooNotConnectedError, WahooUnauthorizedError) as exc:
        raise ConflictError("Wahoo no está conectado o hay que volver a conectarlo.") from exc
    except WahooRateLimitError as exc:
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        raise TooManyRequestsError(
            "Se ha alcanzado el límite de peticiones a Wahoo. Inténtalo más tarde.",
            headers=headers,
        ) from exc
    except WahooApiError as exc:
        raise BadGatewayError("Wahoo no ha respondido correctamente. Inténtalo más tarde.") from exc
    return SyncOut(created=result.created, updated=result.updated, unchanged=result.unchanged)
