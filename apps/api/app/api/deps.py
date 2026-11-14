"""Dependencias comunes de FastAPI: configuración, BD, usuario autenticado y clave interna."""

import secrets
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import AuthenticatedUser, TokenVerifier
from app.db.session import Database

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
