"""Perfil, umbrales y disponibilidad del atleta autenticado.

Todo se filtra por el atleta del JWT. Contrato: #10 (`openapi.json`).
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.athlete import (
    CurrentThresholdOut,
    ProfileOut,
    ProfilePatch,
    ThresholdCreate,
    ThresholdOut,
    WeekAvailability,
)
from app.schemas.common import error_responses
from app.services import athletes, availability, thresholds

router = APIRouter(prefix="/athlete", tags=["athlete"])


@router.get("/profile", responses=error_responses())
def get_profile(user: CurrentUser, db: DbSession) -> ProfileOut:
    """Perfil del atleta. Si no existe todavía, se crea con los valores por defecto."""
    return ProfileOut.model_validate(athletes.get_or_create_profile(db, user.id))


@router.patch("/profile", responses=error_responses())
def update_profile(user: CurrentUser, db: DbSession, body: ProfilePatch) -> ProfileOut:
    """Actualiza sólo los campos enviados y devuelve el perfil completo."""
    profile = athletes.update_profile(db, user.id, body.model_dump(exclude_unset=True))
    return ProfileOut.model_validate(profile)


@router.get("/thresholds", responses=error_responses())
def list_thresholds(user: CurrentUser, db: DbSession) -> list[ThresholdOut]:
    """Historial de umbrales, del más reciente al más antiguo (por `effective_from`)."""
    return [ThresholdOut.model_validate(row) for row in thresholds.list_thresholds(db, user.id)]


@router.post("/thresholds", status_code=status.HTTP_201_CREATED, responses=error_responses(409))
def create_threshold(user: CurrentUser, db: DbSession, body: ThresholdCreate) -> ThresholdOut:
    """Registra umbrales vigentes desde `effective_from`. 409 si ya hay umbrales en esa fecha."""
    threshold = thresholds.create_threshold(db, user.id, body.model_dump())
    return ThresholdOut.model_validate(threshold)


@router.get("/thresholds/current", responses=error_responses(404))
def get_current_threshold(
    user: CurrentUser,
    db: DbSession,
    on: Annotated[
        date | None,
        Query(description="Fecha de referencia. Por defecto, hoy en la zona horaria del atleta."),
    ] = None,
) -> CurrentThresholdOut:
    """Umbral vigente en la fecha y zonas calculadas a partir de él. 404 si no hay ninguno."""
    on = on or thresholds.today_for(db, user.id)
    threshold = thresholds.current_threshold(db, user.id, on)
    return CurrentThresholdOut(
        on=on,
        threshold=ThresholdOut.model_validate(threshold),
        zones=thresholds.zones_for(threshold),
    )


@router.get("/availability", responses=error_responses())
def get_availability(user: CurrentUser, db: DbSession) -> WeekAvailability:
    """Disponibilidad de los 7 días (con valores por defecto en los días sin rellenar)."""
    return availability.get_week(db, user.id)


@router.put("/availability", responses=error_responses())
def replace_availability(
    user: CurrentUser, db: DbSession, body: WeekAvailability
) -> WeekAvailability:
    """Sustituye la disponibilidad de la semana entera (hay que enviar los 7 días)."""
    return availability.replace_week(db, user.id, body)
