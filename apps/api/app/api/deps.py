"""Dependencias comunes de FastAPI: configuración, BD, usuario autenticado y clave interna."""

import secrets
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.crypto import TokenCipher
from app.core.errors import ForbiddenError, ServiceUnavailableError, UnauthorizedError
from app.core.oauth_state import OAuthStateSigner
from app.core.security import AuthenticatedUser, TokenVerifier
from app.db.session import Database
from app.integrations.wahoo.client import WahooClient

_bearer = HTTPBearer(auto_error=False, description="JWT de Supabase Auth")


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database


def get_token_verifier(request: Request) -> TokenVerifier:
    verifier: TokenVerifier = request.app.state.token_verifier
    return verifier


def get_token_cipher(request: Request) -> TokenCipher:
    cipher: TokenCipher | None = request.app.state.token_cipher
    if cipher is None:
        raise ServiceUnavailableError("Cifrado de tokens no configurado.")
    return cipher


def get_state_signer(request: Request) -> OAuthStateSigner:
    signer: OAuthStateSigner | None = request.app.state.state_signer
    if signer is None:
        raise ServiceUnavailableError("Firma de OAuth no configurada.")
    return signer


def get_wahoo_client(request: Request) -> WahooClient:
    client: WahooClient | None = request.app.state.wahoo_client
    if client is None:
        raise ServiceUnavailableError("Integración con Wahoo no configurada.")
    return client


def get_db_session(database: Annotated[Database, Depends(get_database)]) -> Iterator[Session]:
    yield from database.session()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> AuthenticatedUser:
    # Dependencia síncrona: FastAPI la ejecuta en un hilo, así que la descarga del JWKS no bloquea.
    if credentials is None:
        raise UnauthorizedError()
    return verifier.verify(credentials.credentials)


def require_internal_api_key(
    settings: Annotated[Settings, Depends(get_settings)],
    x_internal_api_key: Annotated[str | None, Header()] = None,
) -> None:
    expected = settings.internal_api_key
    if expected is None:
        raise ForbiddenError("API interna deshabilitada.")
    if x_internal_api_key is None or not secrets.compare_digest(
        x_internal_api_key.encode(), expected.get_secret_value().encode()
    ):
        raise UnauthorizedError("Clave interna no válida.")


SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[Database, Depends(get_database)]
DbSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
TokenCipherDep = Annotated[TokenCipher, Depends(get_token_cipher)]
StateSignerDep = Annotated[OAuthStateSigner, Depends(get_state_signer)]
WahooClientDep = Annotated[WahooClient, Depends(get_wahoo_client)]
