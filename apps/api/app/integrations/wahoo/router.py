"""Callback OAuth de Wahoo: la Redirect URI registrada en las apps de Wahoo.

Ruta pública (Wahoo redirige aquí el navegador del usuario). El usuario se identifica con el
`state` firmado; el código se canjea en el servidor y el usuario vuelve a la app sin tokens.
"""

import logging
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.api.deps import DbSession, SettingsDep, StateSignerDep, TokenCipherDep, WahooClientDep
from app.core.config import Settings
from app.core.oauth_state import InvalidStateError, Platform
from app.integrations.wahoo import service
from app.integrations.wahoo.client import WahooAuthError
from app.models import Provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/wahoo", tags=["wahoo"])


def _return_to_app(settings: Settings, platform: Platform, status: str, reason: str = "") -> str:
    base = settings.app_return_url_mobile
    if platform == "web" and settings.app_return_url_web:
        base = settings.app_return_url_web
    params = {"provider": "wahoo", "status": status}
    if reason:
        params["reason"] = reason
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{urlencode(params)}"


@router.get("/callback", response_class=RedirectResponse, status_code=302)
def wahoo_callback(
    settings: SettingsDep,
    signer: StateSignerDep,
    cipher: TokenCipherDep,
    client: WahooClientDep,
    db: DbSession,
    state: Annotated[str, Query()] = "",
    code: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    try:
        oauth_state = signer.verify(state, provider=Provider.WAHOO)
    except InvalidStateError as exc:
        logger.warning("Callback de Wahoo con state no válido: %s", exc)
        return RedirectResponse(_return_to_app(settings, "mobile", "error", "invalid_state"), 302)

    platform = oauth_state.platform
    if error or not code:
        reason = "access_denied" if error == "access_denied" else "authorization_failed"
        return RedirectResponse(_return_to_app(settings, platform, "error", reason), 302)

    try:
        tokens = client.exchange_code(code)
    except WahooAuthError as exc:
        logger.warning("Fallo al canjear el código de Wahoo: %s", exc)
        return RedirectResponse(_return_to_app(settings, platform, "error", "token_exchange"), 302)

    service.save_tokens(db, cipher, oauth_state.user_id, tokens)
    logger.info("Wahoo conectado para el usuario %s", oauth_state.user_id)
    return RedirectResponse(_return_to_app(settings, platform, "connected"), 302)
