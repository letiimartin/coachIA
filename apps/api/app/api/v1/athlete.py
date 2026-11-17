"""Perfil, umbrales y disponibilidad del atleta autenticado.

Contrato (#10): los endpoints están declarados y validan la entrada, pero aún responden 501.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser
from app.core.errors import NotImplementedApiError
from app.schemas.athlete import (
    CurrentThresholdOut,
    ProfileOut,
    ProfilePatch,
    ThresholdCreate,
    ThresholdOut,
    WeekAvailability,
)
from app.schemas.common import error_responses

router = APIRouter(prefix="/athlete", tags=["athlete"])


@router.get("/profile", responses=error_responses())
def get_profile(user: CurrentUser) -> ProfileOut:
    """Perfil del atleta. Si no existe todavía, se crea con los valores por defecto."""
    raise NotImplementedApiError()


@router.patch("/profile", responses=error_responses())
def update_profile(user: CurrentUser, body: ProfilePatch) -> ProfileOut:
    """Actualiza sólo los campos enviados y devuelve el perfil completo."""
    raise NotImplementedApiError()


@router.get("/thresholds", responses=error_responses())
def list_thresholds(user: CurrentUser) -> list[ThresholdOut]:
    """Historial de umbrales, del más reciente al más antiguo (por `effective_from`)."""
    raise NotImplementedApiError()


@router.post("/thresholds", status_code=status.HTTP_201_CREATED, responses=error_responses(409))
def create_threshold(user: CurrentUser, body: ThresholdCreate) -> ThresholdOut:
    """Registra umbrales vigentes desde `effective_from`. 409 si ya hay umbrales en esa fecha."""
    raise NotImplementedApiError()


@router.get("/thresholds/current", responses=error_responses(404))
def get_current_threshold(
    user: CurrentUser,
    on: Annotated[
        date | None,
        Query(description="Fecha de referencia. Por defecto, hoy en la zona horaria del atleta."),
    ] = None,
) -> CurrentThresholdOut:
    """Umbral vigente en la fecha y zonas calculadas a partir de él. 404 si no hay ninguno."""
    raise NotImplementedApiError()


@router.get("/availability", responses=error_responses())
def get_availability(user: CurrentUser) -> WeekAvailability:
    """Disponibilidad de los 7 días (con valores por defecto en los días sin rellenar)."""
    raise NotImplementedApiError()


@router.put("/availability", responses=error_responses())
def replace_availability(user: CurrentUser, body: WeekAvailability) -> WeekAvailability:
    """Sustituye la disponibilidad de la semana entera (hay que enviar los 7 días)."""
    raise NotImplementedApiError()
