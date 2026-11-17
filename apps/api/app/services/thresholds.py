"""Historial de umbrales del atleta y zonas calculadas a partir del umbral vigente."""

import uuid
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from psycopg import errors as pg_errors
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.metrics.zones import HrZoneSport, Zone, hr_zones, power_zones
from app.models import AthleteThreshold
from app.schemas.athlete import ZoneOut, ZonesOut
from app.services.athletes import athlete_timezone, ensure_athlete_profile

_DUPLICATE_DATE = "Ya hay umbrales registrados en esa fecha."


def list_thresholds(session: Session, user_id: uuid.UUID) -> list[AthleteThreshold]:
    """Del más reciente al más antiguo (por `effective_from`)."""
    return list(
        session.scalars(
            sa.select(AthleteThreshold)
            .where(AthleteThreshold.user_id == user_id)
            .order_by(AthleteThreshold.effective_from.desc())
        )
    )


def create_threshold(
    session: Session, user_id: uuid.UUID, values: dict[str, Any]
) -> AthleteThreshold:
    """Registra un juego de umbrales. 409 si ya hay uno con la misma `effective_from`."""
    ensure_athlete_profile(session, user_id)
    exists = session.scalar(
        sa.select(sa.literal(True)).where(
            AthleteThreshold.user_id == user_id,
            AthleteThreshold.effective_from == values["effective_from"],
        )
    )
    if exists:
        session.rollback()
        raise ConflictError(_DUPLICATE_DATE)
    threshold = AthleteThreshold(user_id=user_id, **values)
    session.add(threshold)
    try:
        session.commit()
    except IntegrityError as exc:
        # Carrera entre dos peticiones simultáneas con la misma fecha.
        session.rollback()
        if isinstance(exc.orig, pg_errors.UniqueViolation):
            raise ConflictError(_DUPLICATE_DATE) from exc
        raise
    session.refresh(threshold)
    return threshold


def today_for(session: Session, user_id: uuid.UUID) -> date:
    """Hoy en la zona horaria del atleta."""
    return datetime.now(ZoneInfo(athlete_timezone(session, user_id))).date()


def current_threshold(session: Session, user_id: uuid.UUID, on: date) -> AthleteThreshold:
    """Fila más reciente con `effective_from <= on`. 404 si no hay ninguna."""
    threshold = session.scalar(
        sa.select(AthleteThreshold)
        .where(AthleteThreshold.user_id == user_id, AthleteThreshold.effective_from <= on)
        .order_by(AthleteThreshold.effective_from.desc())
        .limit(1)
    )
    if threshold is None:
        raise NotFoundError("No hay umbrales registrados en esa fecha.")
    return threshold


def _zones_out(zones: tuple[Zone, ...]) -> list[ZoneOut]:
    return [ZoneOut.from_zone(zone) for zone in zones]


def zones_for(threshold: AthleteThreshold) -> ZonesOut:
    """Zonas de potencia (Coggan sobre FTP) y de FC (Friel sobre LTHR), si hay umbral."""
    ftp, lthr = threshold.ftp_w, threshold.lthr_bpm
    return ZonesOut(
        power=_zones_out(power_zones(ftp)) if ftp is not None else None,
        hr_cycling=_zones_out(hr_zones(lthr, HrZoneSport.CYCLING)) if lthr is not None else None,
        hr_running=_zones_out(hr_zones(lthr, HrZoneSport.RUNNING)) if lthr is not None else None,
    )
