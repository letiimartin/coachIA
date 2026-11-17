"""Calendario del atleta: carreras, viajes, salud, eventos sociales y no disponibilidad.

Contrato (#10): los endpoints están declarados y validan la entrada, pero aún responden 501.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser
from app.core.errors import NotImplementedApiError
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventOut,
    CalendarEventPatch,
    CalendarRange,
)
from app.schemas.common import error_responses

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/events", responses=error_responses())
def list_events(
    user: CurrentUser, date_range: Annotated[CalendarRange, Query()]
) -> list[CalendarEventOut]:
    """Eventos que se solapan con el rango `[from, to]`, ordenados por `start_at`. Sin paginar."""
    raise NotImplementedApiError()


@router.post("/events", status_code=status.HTTP_201_CREATED, responses=error_responses())
def create_event(user: CurrentUser, body: CalendarEventCreate) -> CalendarEventOut:
    raise NotImplementedApiError()


@router.patch("/events/{event_id}", responses=error_responses(404, 409))
def update_event(user: CurrentUser, event_id: UUID, body: CalendarEventPatch) -> CalendarEventOut:
    """Actualiza sólo los campos enviados. 409 si el evento resultante no es coherente."""
    raise NotImplementedApiError()


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=error_responses(404),
)
def delete_event(user: CurrentUser, event_id: UUID) -> None:
    """Borra el evento (y sus datos de carrera, si los tiene)."""
    raise NotImplementedApiError()
