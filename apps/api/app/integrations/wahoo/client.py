"""Cliente HTTP de la Wahoo Cloud API (OAuth).

Endpoints y parámetros tomados de la integración que ya funcionaba en LetiSmartCoach:
- GET  {base}/oauth/authorize  (client_id, redirect_uri, response_type=code, scope, state)
- POST {base}/oauth/token      (form: authorization_code o refresh_token + client_id/secret)
Pendiente de verificar con la documentación oficial: listado de workouts, resúmenes y FIT (sync).
"""

import logging
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

DEFAULT_EXPIRES_IN = 7200


class WahooAuthError(Exception):
    """Wahoo rechazó el intercambio o el refresco del token, o respondió algo inesperado."""


@dataclass(frozen=True, slots=True)
class WahooTokens:
    access_token: str
    refresh_token: str | None
    expires_in: int
    scopes: list[str]


class WahooClient:
    def __init__(self, settings: Settings, http: httpx.Client):
        if not settings.wahoo_client_id or settings.wahoo_client_secret is None:
            raise ValueError("Faltan WAHOO_CLIENT_ID o WAHOO_CLIENT_SECRET.")
        self._client_id = settings.wahoo_client_id
        self._client_secret = settings.wahoo_client_secret.get_secret_value()
        self._redirect_uri = settings.wahoo_redirect_uri
        self._scopes = settings.wahoo_scopes
        self._base = settings.wahoo_api_base_url.rstrip("/")
        self._http = http

    def authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "response_type": "code",
                "scope": self._scopes,
                "state": state,
            }
        )
        return f"{self._base}/oauth/authorize?{query}"

    def exchange_code(self, code: str) -> WahooTokens:
        return self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._redirect_uri,
            }
        )

    def refresh(self, refresh_token: str) -> WahooTokens:
        return self._token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})

    def _token_request(self, data: dict[str, str]) -> WahooTokens:
        form = {**data, "client_id": self._client_id, "client_secret": self._client_secret}
        try:
            response = self._http.post(f"{self._base}/oauth/token", data=form, timeout=15)
        except httpx.HTTPError as exc:
            raise WahooAuthError(f"Error de red con Wahoo: {type(exc).__name__}") from exc
        if response.status_code != 200:
            # El cuerpo puede contener detalles útiles, pero nunca se registran los tokens.
            logger.warning("Wahoo /oauth/token respondió %s", response.status_code)
            raise WahooAuthError(f"Wahoo respondió {response.status_code}")
        try:
            body = response.json()
            return WahooTokens(
                access_token=str(body["access_token"]),
                refresh_token=body.get("refresh_token"),
                expires_in=int(body.get("expires_in") or DEFAULT_EXPIRES_IN),
                scopes=str(body.get("scope") or "").split(),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise WahooAuthError("Respuesta de token no válida") from exc

    def close(self) -> None:
        self._http.close()
