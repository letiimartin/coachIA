"""Operaciones sobre el perfil del atleta."""

import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import AthleteProfile


def ensure_athlete_profile(session: Session, user_id: uuid.UUID) -> None:
    """Crea el perfil vacío del atleta si aún no existe (idempotente, sin commit)."""
    session.execute(
        insert(AthleteProfile)
        .values(user_id=user_id)
        .on_conflict_do_nothing(index_elements=[AthleteProfile.user_id])
    )
