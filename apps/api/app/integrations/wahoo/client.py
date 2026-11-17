"""Cliente HTTP de la Wahoo Cloud API (OAuth).

Endpoints verificados con la documentación oficial (https://cloud-api.wahooligan.com):
- GET  {base}/oauth/authorize  (client_id, redirect_uri, response_type=code, scope, state)
- POST {base}/oauth/token      (form: authorization_code o refresh_token + client_id/secret)
- GET  {base}/v1/workouts      (page, per_page; ordenados por `starts` descendente)
  Respuesta: {"workouts": [...], "total", "page", "per_page", "order", "sort"}.
- GET  {base}/v1/workouts/:id/workout_summary  (resultados del workout y `file.url` del FIT)
Errores: códigos HTTP (401 token no válido, 429 límite de peticiones, 5xx). Los límites se
informan en las cabeceras X-RateLimit-*; X-RateLimit-Reset son los segundos hasta el reinicio.
"""

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

DEFAULT_EXPIRES_IN = 7200
# La documentación no fija un máximo para per_page; 50 reduce peticiones sin pedir páginas enormes.
WORKOUTS_PER_PAGE = 50
API_TIMEOUT_SECONDS = 20


class WahooAuthError(Exception):
    """Wahoo rechazó el intercambio o el refresco del token, o respondió algo inesperado."""


class WahooApiError(Exception):
    """Error al llamar a la API de datos de Wahoo (red, 5xx o respuesta inesperada)."""


class WahooUnauthorizedError(WahooApiError):
    """Wahoo rechazó el access token (401/403): hay que volver a conectar la cuenta."""


class WahooRateLimitError(WahooApiError):
    """Wahoo respondió 429: se ha superado el límite de peticiones."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class WahooNotFoundError(WahooApiError):
    """El recurso no existe (p. ej. un workout sin resumen o borrado)."""


@dataclass(frozen=True, slots=True)
class WorkoutsPage:
    workouts: list[dict[str, Any]]
    total: int
    page: int
    per_page: int


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

    def list_workouts(
        self, access_token: str, page: int = 1, per_page: int = WORKOUTS_PER_PAGE
    ) -> WorkoutsPage:
        """Una página de workouts del usuario, del más reciente al más antiguo (por `starts`)."""
        body = self._get(access_token, "/v1/workouts", {"page": page, "per_page": per_page})
        workouts = body.get("workouts") if isinstance(body, dict) else None
        if not isinstance(workouts, list) or not all(isinstance(w, dict) for w in workouts):
            raise WahooApiError("Respuesta de /v1/workouts no válida")
        return WorkoutsPage(
            workouts=workouts,
            total=_as_int(body.get("total"), default=len(workouts)),
            page=_as_int(body.get("page"), default=page),
            per_page=_as_int(body.get("per_page"), default=per_page),
        )

    def get_workout_summary(self, access_token: str, workout_id: int | str) -> dict[str, Any]:
        """Resumen (resultados) de un workout. WahooNotFoundError si no existe."""
        body = self._get(access_token, f"/v1/workouts/{workout_id}/workout_summary")
        if not isinstance(body, dict):
            raise WahooApiError("Respuesta de workout_summary no válida")
        return body

    def _get(self, access_token: str, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = self._http.get(
                f"{self._base}{path}",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=API_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise WahooApiError(f"Error de red con Wahoo: {type(exc).__name__}") from exc
        status = response.status_code
        if status in (401, 403):
            raise WahooUnauthorizedError(f"Wahoo rechazó el token ({status})")
        if status == 404:
            raise WahooNotFoundError("Recurso de Wahoo no encontrado")
        if status == 429:
            retry_after = _as_int(response.headers.get("X-RateLimit-Reset"), default=0) or None
            raise WahooRateLimitError("Límite de peticiones de Wahoo superado", retry_after)
        if status != 200:
            # Sólo se registra la ruta (sin query string ni cabeceras).
            logger.warning("Wahoo GET %s respondió %s", path, status)
            raise WahooApiError(f"Wahoo respondió {status}")
        try:
            return response.json()
        except ValueError as exc:
            raise WahooApiError("Respuesta de Wahoo no es JSON") from exc

    def close(self) -> None:
        self._http.close()


def _as_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
