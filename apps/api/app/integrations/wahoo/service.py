"""Casos de uso de la integración con Wahoo: conectar, obtener token válido y desconectar."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.crypto import TokenCipher, TokenCipherError
from app.integrations.wahoo.client import WahooAuthError, WahooClient, WahooTokens
from app.models import Integration, IntegrationStatus, Provider
from app.services.athletes import ensure_athlete_profile

logger = logging.getLogger(__name__)

# Se refresca el token si caduca en menos de este margen.
REFRESH_MARGIN = timedelta(minutes=5)


class WahooNotConnectedError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def save_tokens(
    session: Session, cipher: TokenCipher, user_id: uuid.UUID, tokens: WahooTokens
) -> Integration:
    """Crea o actualiza la integración del usuario con los tokens cifrados."""
    ensure_athlete_profile(session, user_id)
    values = {
        "access_token_enc": cipher.encrypt(tokens.access_token),
        "refresh_token_enc": cipher.encrypt(tokens.refresh_token) if tokens.refresh_token else None,
        "token_expires_at": _now() + timedelta(seconds=tokens.expires_in),
        "scopes": tokens.scopes,
        "status": IntegrationStatus.ACTIVE,
        "last_error": None,
    }
    statement = (
        insert(Integration)
        .values(user_id=user_id, provider=Provider.WAHOO, **values)
        .on_conflict_do_update(constraint="uq_integrations_user_id_provider", set_=values)
        .returning(Integration.id)
    )
    integration_id = session.execute(statement).scalar_one()
    session.commit()
    integration = session.get(Integration, integration_id, populate_existing=True)
    if integration is None:  # pragma: no cover - acabamos de insertarla en la misma sesión
        raise RuntimeError("La integración no se encuentra tras guardarla.")
    return integration


def get_integration(session: Session, user_id: uuid.UUID) -> Integration | None:
    return session.scalar(
        select(Integration).where(
            Integration.user_id == user_id, Integration.provider == Provider.WAHOO
        )
    )


def get_valid_access_token(
    session: Session, cipher: TokenCipher, client: WahooClient, user_id: uuid.UUID
) -> str:
    """Devuelve un access token vigente, refrescándolo si está a punto de caducar."""
    integration = get_integration(session, user_id)
    if (
        integration is None
        or integration.status == IntegrationStatus.REVOKED
        or integration.access_token_enc is None
    ):
        raise WahooNotConnectedError()

    expires_at = integration.token_expires_at
    if expires_at is not None and expires_at - _now() > REFRESH_MARGIN:
        return cipher.decrypt(integration.access_token_enc)

    if integration.refresh_token_enc is None:
        _mark_error(session, integration, "Token caducado y sin refresh token")
        raise WahooNotConnectedError()
    try:
        tokens = client.refresh(cipher.decrypt(integration.refresh_token_enc))
    except (WahooAuthError, TokenCipherError) as exc:
        _mark_error(session, integration, f"No se pudo refrescar el token: {exc}")
        raise WahooNotConnectedError() from exc

    # Si Wahoo no devuelve un refresh token nuevo, se conserva el anterior.
    if tokens.refresh_token is None:
        tokens = WahooTokens(
            access_token=tokens.access_token,
            refresh_token=cipher.decrypt(integration.refresh_token_enc),
            expires_in=tokens.expires_in,
            scopes=tokens.scopes or integration.scopes,
        )
    save_tokens(session, cipher, user_id, tokens)
    return tokens.access_token


def disconnect(session: Session, user_id: uuid.UUID) -> bool:
    """Borra los tokens y marca la integración como revocada. Devuelve False si no existía."""
    integration = get_integration(session, user_id)
    if integration is None:
        return False
    integration.access_token_enc = None
    integration.refresh_token_enc = None
    integration.token_expires_at = None
    integration.status = IntegrationStatus.REVOKED
    session.commit()
    return True


def _mark_error(session: Session, integration: Integration, message: str) -> None:
    logger.warning("Integración Wahoo %s en error: %s", integration.id, message)
    integration.status = IntegrationStatus.ERROR
    integration.last_error = message
    session.commit()
