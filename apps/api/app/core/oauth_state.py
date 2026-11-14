"""Parámetro `state` de OAuth firmado.

El `state` viaja al proveedor y vuelve en el callback. Al ir firmado (JWT HS256 con caducidad
corta), el callback sabe a qué usuario pertenece la autorización sin sesión de navegador y
rechaza peticiones falsificadas (CSRF).
"""

import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Literal

import jwt

Platform = Literal["mobile", "web"]

_AUDIENCE = "coachia:oauth-state"
_TTL_SECONDS = 600


class InvalidStateError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class OAuthState:
    user_id: uuid.UUID
    provider: str
    platform: Platform


class OAuthStateSigner:
    def __init__(self, secret: str, ttl_seconds: int = _TTL_SECONDS):
        self._secret = secret
        self._ttl = ttl_seconds

    def sign(self, state: OAuthState) -> str:
        now = int(time.time())
        payload = {
            "sub": str(state.user_id),
            "provider": state.provider,
            "platform": state.platform,
            "nonce": secrets.token_urlsafe(8),
            "aud": _AUDIENCE,
            "iat": now,
            "exp": now + self._ttl,
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def verify(self, token: str, *, provider: str) -> OAuthState:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                audience=_AUDIENCE,
                options={"require": ["exp", "sub", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidStateError(type(exc).__name__) from exc
        if claims.get("provider") != provider:
            raise InvalidStateError("provider")
        platform = claims.get("platform")
        if platform not in ("mobile", "web"):
            raise InvalidStateError("platform")
        try:
            user_id = uuid.UUID(str(claims["sub"]))
        except ValueError as exc:
            raise InvalidStateError("sub") from exc
        return OAuthState(user_id=user_id, provider=provider, platform=platform)
