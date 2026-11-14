"""Webhook de Strava (suscripción y recepción de eventos).

Migrado desde el esqueleto inicial. De momento sólo valida y registra los eventos; la
importación de actividades llegará cuando se decida usar Strava como fuente (ver docs, 12.4).
"""

import logging
import secrets
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import SettingsDep
from app.core.errors import ForbiddenError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/strava", tags=["webhooks"])


class StravaEvent(BaseModel):
    object_type: Literal["activity", "athlete"]
    object_id: int
    aspect_type: Literal["create", "update", "delete"]
    owner_id: int
    subscription_id: int
    event_time: int
    updates: dict[str, Any] = Field(default_factory=dict)


class ReceivedResponse(BaseModel):
    received: bool


@router.get("")
def verify_subscription(
    settings: SettingsDep,
    mode: Annotated[str, Query(alias="hub.mode")],
    verify_token: Annotated[str, Query(alias="hub.verify_token")],
    challenge: Annotated[str, Query(alias="hub.challenge")],
) -> dict[str, str]:
    expected = settings.strava_verify_token
    if (
        expected is None
        or mode != "subscribe"
        or not secrets.compare_digest(verify_token.encode(), expected.get_secret_value().encode())
    ):
        raise ForbiddenError("Token de verificación no válido.")
    return {"hub.challenge": challenge}


@router.post("")
def receive_event(event: StravaEvent) -> ReceivedResponse:
    logger.info(
        "Evento Strava: %s %s id=%s owner=%s",
        event.object_type,
        event.aspect_type,
        event.object_id,
        event.owner_id,
    )
    return ReceivedResponse(received=True)
