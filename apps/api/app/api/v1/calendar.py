"""Calendario del atleta: carreras, viajes, salud, eventos sociales y no disponibilidad.

Todo se filtra por el atleta del JWT: un evento de otro atleta responde 404. Contrato: #10.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventOut,
    CalendarEventPatch,
    CalendarRange,
)
from app.schemas.common import error_responses
from app.services import calendar as calendar_service

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/events", responses=error_responses())
def list_events(
    user: CurrentUser, db: DbSession, date_range: Annotated[CalendarRange, Query()]
) -> list[CalendarEventOut]:
    """Eventos que se solapan con el rango `[from, to]`, ordenados por `start_at`. Sin paginar."""
    return calendar_service.list_events(db, user.id, date_range.from_, date_range.to)


@router.post("/events", status_code=status.HTTP_201_CREATED, responses=error_responses())
def create_event(user: CurrentUser, db: DbSession, body: CalendarEventCreate) -> CalendarEventOut:
    return calendar_service.create_event(db, user.id, body)


@router.patch("/events/{event_id}", responses=error_responses(404, 409))
def update_event(
    user: CurrentUser, db: DbSession, event_id: UUID, body: CalendarEventPatch
) -> CalendarEventOut:
    """Actualiza sólo los campos enviados. 409 si el evento resultante no es coherente."""
    return calendar_service.update_event(db, user.id, event_id, body)


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=error_responses(404),
)
def delete_event(user: CurrentUser, db: DbSession, event_id: UUID) -> None:
    """Borra el evento (y sus datos de carrera, si los tiene)."""
    calendar_service.delete_event(db, user.id, event_id)
