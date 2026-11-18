"""Tests de umbral: propuestas calculadas a partir del FIT de una actividad (#42).

La API detecta el intervalo del test y calcula el umbral (de forma determinista); el resultado
es sólo una propuesta hasta que la atleta la acepta. Todo se filtra por el atleta del JWT.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, WahooClientDep
from app.core.errors import BadGatewayError, TooManyRequestsError, UnprocessableError
from app.integrations.wahoo.client import (
    WahooApiError,
    WahooNotFoundError,
    WahooRateLimitError,
)
from app.models.threshold_proposal import ProposalStatus
from app.schemas.common import error_responses
from app.schemas.threshold_proposals import ThresholdProposalCreate, ThresholdProposalOut
from app.services import threshold_proposals

router = APIRouter(prefix="/athlete/threshold-proposals", tags=["threshold-proposals"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422, 429, 502, 503),
)
def create_proposal(
    user: CurrentUser, db: DbSession, client: WahooClientDep, body: ThresholdProposalCreate
) -> ThresholdProposalOut:
    """Descarga el FIT de la actividad, detecta el test y crea una propuesta **pendiente**.

    No cambia ningún umbral. Errores 422 con `code`: `not_cycling`, `fit_unavailable` (sin
    fichero), `fit_invalid` (dañado o sin registros), `no_power_data`, `test_too_short`,
    `insufficient_data` (demasiados huecos) y `ftp_out_of_range`. 409 si ya hay una propuesta
    pendiente de esa actividad.
    """

    def fetch_fit(url: str) -> bytes:
        try:
            return client.download_fit(url)
        except WahooNotFoundError as exc:
            raise UnprocessableError(
                "El fichero FIT de la actividad ya no está disponible en Wahoo.",
                code="fit_unavailable",
            ) from exc
        except WahooRateLimitError as exc:
            raise TooManyRequestsError(
                "Se ha alcanzado el límite de peticiones a Wahoo. Inténtalo más tarde."
            ) from exc
        except WahooApiError as exc:
            raise BadGatewayError("No se ha podido descargar el FIT de Wahoo.") from exc

    proposal = threshold_proposals.create_proposal(
        db, user.id, body.activity_id, body.protocol, fetch_fit
    )
    return ThresholdProposalOut.model_validate(proposal)


@router.get("", responses=error_responses())
def list_proposals(
    user: CurrentUser,
    db: DbSession,
    status_filter: Annotated[
        ProposalStatus | None, Query(alias="status", description="Filtra por estado.")
    ] = None,
) -> list[ThresholdProposalOut]:
    """Propuestas del atleta, de la más reciente a la más antigua."""
    return [
        ThresholdProposalOut.model_validate(row)
        for row in threshold_proposals.list_proposals(db, user.id, status_filter)
    ]


@router.get("/{proposal_id}", responses=error_responses(404))
def get_proposal(user: CurrentUser, db: DbSession, proposal_id: uuid.UUID) -> ThresholdProposalOut:
    return ThresholdProposalOut.model_validate(
        threshold_proposals.get_proposal(db, user.id, proposal_id)
    )


@router.post("/{proposal_id}/accept", responses=error_responses(404, 409))
def accept_proposal(
    user: CurrentUser, db: DbSession, proposal_id: uuid.UUID
) -> ThresholdProposalOut:
    """Acepta la propuesta: crea un umbral nuevo vigente desde `test_date` con `source = test`.

    El umbral nuevo lleva el FTP propuesto y copia el resto de valores del umbral vigente ese
    día. No fuerza ningún recálculo histórico: sólo se rellena la carga de las actividades que
    no la tienen y se regenera la forma. 409 si la propuesta no está pendiente o si ya hay
    umbrales registrados en `test_date`.
    """
    return ThresholdProposalOut.model_validate(
        threshold_proposals.accept_proposal(db, user.id, proposal_id)
    )


@router.post("/{proposal_id}/reject", responses=error_responses(404, 409))
def reject_proposal(
    user: CurrentUser, db: DbSession, proposal_id: uuid.UUID
) -> ThresholdProposalOut:
    """Rechaza la propuesta. No cambia ningún umbral. 409 si no está pendiente."""
    return ThresholdProposalOut.model_validate(
        threshold_proposals.reject_proposal(db, user.id, proposal_id)
    )
