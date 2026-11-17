"""Calendario del atleta: eventos y, en los de tipo carrera, sus datos (`races`)."""

import uuid
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import CalendarEvent, EventKind, Race
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventOut,
    CalendarEventPatch,
    RaceCreate,
    RaceOut,
    RacePatch,
)
from app.services.athletes import athlete_timezone, ensure_athlete_profile

_EVENT_NOT_FOUND = "Evento no encontrado."


def to_out(event: CalendarEvent, race: Race | None) -> CalendarEventOut:
    return CalendarEventOut(
        id=event.id,
        kind=event.kind,
        title=event.title,
        start_at=event.start_at,
        end_at=event.end_at,
        all_day=event.all_day,
        training_impact=event.training_impact,
        notes=event.notes,
        details=event.details,
        race=RaceOut.model_validate(race) if race is not None else None,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _race_values(race: RaceCreate | RacePatch) -> dict[str, Any]:
    """Valores de carrera listos para la BD (la URL se guarda como texto).

    De `RaceCreate` se toman todos los campos (con sus valores por defecto); de `RacePatch`,
    sólo los enviados.
    """
    values = race.model_dump(exclude_unset=isinstance(race, RacePatch))
    if values.get("source_url") is not None:
        values["source_url"] = str(values["source_url"])
    return values


def list_events(
    session: Session, user_id: uuid.UUID, from_: date, to: date
) -> list[CalendarEventOut]:
    """Eventos que se solapan con `[from_, to]` (días completos en la zona del atleta)."""
    tz = ZoneInfo(athlete_timezone(session, user_id))
    range_start = datetime.combine(from_, time.min, tzinfo=tz)
    range_end = datetime.combine(to + timedelta(days=1), time.min, tzinfo=tz)
    events = list(
        session.scalars(
            sa.select(CalendarEvent)
            .where(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_at < range_end,
                sa.func.coalesce(CalendarEvent.end_at, CalendarEvent.start_at) >= range_start,
            )
            .order_by(CalendarEvent.start_at, CalendarEvent.id)
        )
    )
    race_ids = [event.id for event in events if event.kind is EventKind.RACE]
    races = (
        {
            race.event_id: race
            for race in session.scalars(
                sa.select(Race).where(Race.user_id == user_id, Race.event_id.in_(race_ids))
            )
        }
        if race_ids
        else {}
    )
    return [to_out(event, races.get(event.id)) for event in events]


def create_event(
    session: Session, user_id: uuid.UUID, body: CalendarEventCreate
) -> CalendarEventOut:
    """Crea el evento; si es una carrera sin `race`, con los valores por defecto."""
    ensure_athlete_profile(session, user_id)
    event = CalendarEvent(user_id=user_id, **body.model_dump(exclude={"race"}))
    session.add(event)
    session.flush()
    race: Race | None = None
    if event.kind is EventKind.RACE:
        race = Race(event_id=event.id, user_id=user_id, **_race_values(body.race or RaceCreate()))
        session.add(race)
    session.commit()
    session.refresh(event)
    if race is not None:
        session.refresh(race)
    return to_out(event, race)


def _get_event(session: Session, user_id: uuid.UUID, event_id: uuid.UUID) -> CalendarEvent:
    event = session.scalar(
        sa.select(CalendarEvent).where(
            CalendarEvent.id == event_id, CalendarEvent.user_id == user_id
        )
    )
    if event is None:
        raise NotFoundError(_EVENT_NOT_FOUND)
    return event


def update_event(
    session: Session, user_id: uuid.UUID, event_id: uuid.UUID, body: CalendarEventPatch
) -> CalendarEventOut:
    """Aplica sólo los campos enviados y comprueba la coherencia del evento resultante.

    - `race` se fusiona con la carrera existente (o con los valores por defecto si no la hay).
    - Si el evento deja de ser una carrera, se borran sus datos de carrera.
    - 409 si `end_at < start_at` o si se envía `race` en un evento que no es carrera.
    """
    event = _get_event(session, user_id, event_id)
    race = session.get(Race, event.id)

    for name, value in body.model_dump(exclude_unset=True, exclude={"race"}).items():
        setattr(event, name, value)

    if event.end_at is not None and event.end_at < event.start_at:
        session.rollback()
        raise ConflictError("end_at no puede ser anterior a start_at.")
    if body.race is not None and event.kind is not EventKind.RACE:
        session.rollback()
        raise ConflictError("race sólo se admite en eventos de tipo 'race'.")

    if event.kind is EventKind.RACE:
        if race is None:
            race = Race(event_id=event.id, user_id=user_id, **_race_values(RaceCreate()))
            session.add(race)
        if body.race is not None:
            for name, value in _race_values(body.race).items():
                setattr(race, name, value)
            race.updated_at = sa.func.now()
    elif race is not None:
        session.delete(race)
        race = None

    event.updated_at = sa.func.now()
    session.commit()
    session.refresh(event)
    if race is not None:
        session.refresh(race)
    return to_out(event, race)


def delete_event(session: Session, user_id: uuid.UUID, event_id: uuid.UUID) -> None:
    """Borra el evento; la carrera asociada se borra en cascada (FK con ON DELETE CASCADE)."""
    result = session.execute(
        sa.delete(CalendarEvent).where(
            CalendarEvent.id == event_id, CalendarEvent.user_id == user_id
        )
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        session.rollback()
        raise NotFoundError(_EVENT_NOT_FOUND)
    session.commit()
