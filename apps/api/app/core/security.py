"""Verificación de los JWT emitidos por Supabase Auth.

- Proyectos nuevos: firma asimétrica (ES256/RS256) con claves públicas en el endpoint JWKS.
- Proyectos antiguos: firma HS256 con el JWT secret heredado (`SUPABASE_JWT_SECRET`).

Se valida firma, caducidad, audiencia y, si hay `SUPABASE_URL`, el emisor.
"""

import logging
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import jwt

from app.core.config import Settings
from app.core.errors import UnauthorizedError

logger = logging.getLogger(__name__)

ASYMMETRIC_ALGORITHMS = frozenset({"ES256", "RS256"})


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: UUID
    email: str | None
    role: str


class SigningKeyProvider(Protocol):
    """Interfaz mínima de `jwt.PyJWKClient`; permite sustituirlo en los tests."""

    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class TokenVerifier:
    def __init__(self, settings: Settings, jwks_client: SigningKeyProvider | None = None):
        self._settings = settings
        if jwks_client is None and settings.supabase_jwks_url:
            jwks_client = jwt.PyJWKClient(
                settings.supabase_jwks_url, cache_keys=True, lifespan=3600
            )
        self._jwks_client = jwks_client

    def verify(self, token: str) -> AuthenticatedUser:
        try:
            algorithm = jwt.get_unverified_header(token).get("alg")
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Token mal formado.") from exc
        if not isinstance(algorithm, str):
            raise UnauthorizedError("Algoritmo de firma no admitido.")

        key = self._resolve_key(token, algorithm)
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=[algorithm],
                audience=self._settings.supabase_jwt_audience,
                issuer=self._settings.supabase_issuer,
                options={"require": ["exp", "sub", "aud"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError("La sesión ha caducado.") from exc
        except jwt.PyJWTError as exc:
            logger.info("JWT rechazado: %s", type(exc).__name__)
            raise UnauthorizedError("Token no válido.") from exc

        try:
            user_id = UUID(str(claims["sub"]))
        except ValueError as exc:
            raise UnauthorizedError("Token no válido.") from exc
        return AuthenticatedUser(
            id=user_id, email=claims.get("email"), role=str(claims.get("role", ""))
        )

    def _resolve_key(self, token: str, algorithm: str) -> Any:
        if algorithm in ASYMMETRIC_ALGORITHMS:
            if self._jwks_client is None:
                raise UnauthorizedError("Verificación de tokens no configurada.")
            try:
                return self._jwks_client.get_signing_key_from_jwt(token).key
            except jwt.PyJWTError as exc:
                logger.warning("No se pudo obtener la clave de firma: %s", type(exc).__name__)
                raise UnauthorizedError("Token no válido.") from exc
        if algorithm == "HS256":
            secret = self._settings.supabase_jwt_secret
            if secret is None:
                raise UnauthorizedError("Verificación de tokens no configurada.")
            return secret.get_secret_value()
        raise UnauthorizedError("Algoritmo de firma no admitido.")
