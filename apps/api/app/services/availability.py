"""Disponibilidad semanal habitual del atleta."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models import AvailabilitySlot
from app.schemas.athlete import AvailabilityDay, WeekAvailability
from app.services.athletes import ensure_athlete_profile


def get_week(session: Session, user_id: uuid.UUID) -> WeekAvailability:
    """Los 7 días; los que no se han rellenado llevan los valores por defecto."""
    slots = {
        slot.weekday: slot
        for slot in session.scalars(
            sa.select(AvailabilitySlot).where(AvailabilitySlot.user_id == user_id)
        )
    }
    return WeekAvailability(
        days=[
            AvailabilityDay.model_validate(slots[weekday])
            if weekday in slots
            else AvailabilityDay(weekday=weekday)
            for weekday in range(7)
        ]
    )


def replace_week(session: Session, user_id: uuid.UUID, week: WeekAvailability) -> WeekAvailability:
    """Sustituye la semana entera en una sola transacción."""
    ensure_athlete_profile(session, user_id)
    session.execute(sa.delete(AvailabilitySlot).where(AvailabilitySlot.user_id == user_id))
    session.add_all(AvailabilitySlot(user_id=user_id, **day.model_dump()) for day in week.days)
    session.commit()
    return get_week(session, user_id)
