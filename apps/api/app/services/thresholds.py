"""Historial de umbrales del atleta y zonas calculadas a partir del umbral vigente."""

import uuid
from datetime import date
from typing import Any

import sqlalchemy as sa
from psycopg import errors as pg_errors
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.metrics.zones import HrZoneSport, Zone, hr_zones, lthr_field_for, zone_model_for
from app.models import AthleteThreshold, Sport
from app.schemas.athlete import ZoneOut, ZonesOut
from app.services import fitness
from app.services.athletes import ensure_athlete_profile

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
    """Registra un juego de umbrales. 409 si ya hay uno con la misma `effective_from`.

    En la misma transacción regenera la forma desde `effective_from` y calcula la carga de las
    actividades que aún no la tienen. No cambia la carga de las que ya la tienen (protección de
    #22): eso sólo lo hace el recálculo histórico explícito (`scripts/recompute_loads.py`).
    """
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
        session.flush()
    except IntegrityError as exc:
        # Carrera entre dos peticiones simultáneas con la misma fecha.
        session.rollback()
        if isinstance(exc.orig, pg_errors.UniqueViolation):
            raise ConflictError(_DUPLICATE_DATE) from exc
        raise
    fitness.recompute_from(session, user_id, threshold.effective_from)
    session.commit()
    session.refresh(threshold)
    return threshold


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
    """Zonas de cada disciplina y de FC, calculadas sobre el umbral vigente (null si falta)."""

    def model_zones(sport: Sport) -> list[ZoneOut] | None:
        model = zone_model_for(sport)
        if model is None:  # pragma: no cover - las tres disciplinas tienen modelo.
            return None
        value = getattr(threshold, model.threshold_field)
        zones = model.zones(None if value is None else float(value))
        return None if zones is None else _zones_out(zones)

    def lthr(sport: Sport) -> int | None:
        field = lthr_field_for(sport)
        return None if field is None else getattr(threshold, field)

    cycling_lthr = lthr(Sport.CYCLING)
    running_lthr = lthr(Sport.RUNNING)
    return ZonesOut(
        power=model_zones(Sport.CYCLING),
        running_pace=model_zones(Sport.RUNNING),
        trail_hr=model_zones(Sport.TRAIL_RUNNING),
        hr_cycling=(
            _zones_out(hr_zones(cycling_lthr, HrZoneSport.CYCLING))
            if cycling_lthr is not None
            else None
        ),
        hr_running=(
            _zones_out(hr_zones(running_lthr, HrZoneSport.RUNNING))
            if running_lthr is not None
            else None
        ),
    )
