"""Operaciones sobre el perfil del atleta."""

import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import AthleteProfile

# Debe coincidir con el server_default de athlete_profiles.timezone.
DEFAULT_TIMEZONE = "Europe/Madrid"


def ensure_athlete_profile(session: Session, user_id: uuid.UUID) -> None:
    """Crea el perfil vacío del atleta si aún no existe (idempotente, sin commit)."""
    session.execute(
        insert(AthleteProfile)
        .values(user_id=user_id)
        .on_conflict_do_nothing(index_elements=[AthleteProfile.user_id])
    )


def get_or_create_profile(session: Session, user_id: uuid.UUID) -> AthleteProfile:
    """Perfil del atleta; si no existe, lo crea con los valores por defecto (y hace commit)."""
    profile = session.get(AthleteProfile, user_id)
    if profile is None:
        ensure_athlete_profile(session, user_id)
        session.commit()
        profile = session.get_one(AthleteProfile, user_id)
    return profile


def update_profile(session: Session, user_id: uuid.UUID, changes: dict[str, Any]) -> AthleteProfile:
    """Aplica sólo los campos recibidos (`None` borra el valor) y devuelve el perfil."""
    profile = get_or_create_profile(session, user_id)
    for name, value in changes.items():
        setattr(profile, name, value)
    profile.updated_at = sa.func.now()
    session.commit()
    session.refresh(profile)
    return profile


def athlete_timezone(session: Session, user_id: uuid.UUID) -> str:
    """Zona horaria del atleta, sin crear el perfil si no existe."""
    timezone = session.scalar(
        sa.select(AthleteProfile.timezone).where(AthleteProfile.user_id == user_id)
    )
    return timezone or DEFAULT_TIMEZONE
