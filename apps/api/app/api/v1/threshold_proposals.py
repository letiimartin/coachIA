"""Tests de umbral: propuestas calculadas a partir del FIT de una actividad (#42, #45).

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
    WahooClient,
    WahooNotFoundError,
    WahooRateLimitError,
)
from app.models.threshold_proposal import ProposalStatus
from app.schemas.common import error_responses
from app.schemas.threshold_proposals import (
    AcceptancePreviewOut,
    ThresholdProposalAccept,
    ThresholdProposalCreate,
    ThresholdProposalOut,
    ThresholdTestAnalysisOut,
)
from app.services import threshold_proposals
from app.services.threshold_proposals import FitFetcher

router = APIRouter(prefix="/athlete/threshold-proposals", tags=["threshold-proposals"])


def _fit_fetcher(client: WahooClient) -> FitFetcher:
    """Descarga del FIT con los errores de Wahoo traducidos a errores de la API."""

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

    return fetch_fit


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
    fichero), `fit_invalid` (dañado o sin registros), y los criterios que bloquean la
    propuesta, con el criterio evaluado (valor medido, umbral, mensaje) en `error.details`:
    `no_power_data`, `test_too_short`, `insufficient_data` (demasiados huecos) y
    `ftp_out_of_range`. 409 si ya hay una propuesta pendiente de esa actividad.
    """
    proposal = threshold_proposals.create_proposal(
        db, user.id, body.activity_id, body.protocol, _fit_fetcher(client)
    )
    return ThresholdProposalOut.model_validate(proposal)


@router.post("/dry-run", responses=error_responses(404, 422, 429, 502, 503))
def dry_run(
    user: CurrentUser, db: DbSession, client: WahooClientDep, body: ThresholdProposalCreate
) -> ThresholdTestAnalysisOut:
    """Análisis de prueba: descarga el FIT y analiza el test **sin crear ninguna propuesta**.

    Devuelve el intervalo detectado, sus métricas, el FTP propuesto y la evaluación de cada
    criterio de calidad. Sirve para validar la descarga y la lectura del FIT. Mismos errores
    que crear la propuesta, salvo el 409 (no se crea nada).
    """
    analysis = threshold_proposals.analyze_activity(
        db, user.id, body.activity_id, body.protocol, _fit_fetcher(client)
    )
    return ThresholdTestAnalysisOut.model_validate(analysis, from_attributes=True)


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


@router.get("/{proposal_id}/preview", responses=error_responses(404, 409))
def preview_acceptance(
    user: CurrentUser, db: DbSession, proposal_id: uuid.UUID
) -> AcceptancePreviewOut:
    """Vista previa de aceptar la propuesta, sin guardar nada.

    `action`: `create_row` (no hay umbrales en `test_date`) o `update_ftp` (ya hay una fila en
    esa fecha; sólo cambiaría su FTP). Incluye el FTP anterior de esa fecha, el propuesto y la
    ventana de vigencia del FTP nuevo; si hay registros posteriores, el aviso
    `later_thresholds` y el siguiente registro. 409 si la propuesta no está pendiente.
    """
    preview = threshold_proposals.preview_acceptance(db, user.id, proposal_id)
    return AcceptancePreviewOut.model_validate(preview, from_attributes=True)


@router.post("/{proposal_id}/accept", responses=error_responses(404, 409))
def accept_proposal(
    user: CurrentUser, db: DbSession, proposal_id: uuid.UUID, body: ThresholdProposalAccept
) -> ThresholdProposalOut:
    """Acepta la propuesta tal como la mostró la vista previa (`action` y `previous_ftp_w`).

    - `create_row`: crea un umbral vigente desde `test_date` con `source = test`, el FTP
      propuesto y el resto de valores copiados del umbral vigente ese día.
    - `update_ftp`: cambia sólo el `ftp_w` de la fila de `test_date`; conserva el resto.

    La fila guarda la propuesta de la que sale su FTP; los registros posteriores no se tocan.
    No lanza ningún recálculo histórico: sólo se rellena la carga de las actividades que no la
    tienen y se regenera la forma. 409 `preview_outdated` (con la vista previa nueva en
    `error.details`) si la acción o el FTP anterior ya no coinciden; 409 `conflict` si la
    propuesta no está pendiente.
    """
    return ThresholdProposalOut.model_validate(
        threshold_proposals.accept_proposal(
            db, user.id, proposal_id, body.action, body.previous_ftp_w
        )
    )


@router.post("/{proposal_id}/reject", responses=error_responses(404, 409))
def reject_proposal(
    user: CurrentUser, db: DbSession, proposal_id: uuid.UUID
) -> ThresholdProposalOut:
    """Rechaza la propuesta. No cambia ningún umbral. 409 si no está pendiente."""
    return ThresholdProposalOut.model_validate(
        threshold_proposals.reject_proposal(db, user.id, proposal_id)
    )
