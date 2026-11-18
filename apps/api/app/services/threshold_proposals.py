"""Propuestas de umbral salidas de un test (#42): crear, listar, aceptar y rechazar.

La propuesta no cambia ningún umbral. Sólo al aceptarla se añade una fila a
`athlete_thresholds` con `source = test`, a través de `thresholds.add_threshold`: el gancho
normal rellena la carga de las actividades que no la tienen y regenera la forma, pero nunca
cambia las cargas existentes (protección de #22). No hay recálculo histórico.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from psycopg import errors as pg_errors
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.integrations.fit import FitError, parse_records
from app.metrics.tests import (
    FtpTestResult,
    Sample,
    ThresholdProtocol,
    ThresholdTestError,
    analyze_ftp_20min,
)
from app.models import Activity, ActivitySource, AthleteThreshold, Sport, ThresholdProposal
from app.models.athlete import ThresholdSource
from app.models.threshold_proposal import ProposalStatus
from app.services import thresholds
from app.services.athletes import athlete_timezone

# Descarga el FIT a partir de su URL. Lanza las excepciones del cliente del proveedor.
FitFetcher = Callable[[str], bytes]

FTP_MIN_W, FTP_MAX_W = 50, 700

# Umbrales que se copian del vigente al aceptar. `legacy_lthr_bpm` no: es de sólo lectura y
# está pendiente de que la autora decida a qué disciplina pertenecía.
_COPIED_FIELDS = (
    "cycling_lthr_bpm",
    "running_lthr_bpm",
    "hr_max_bpm",
    "hr_rest_bpm",
    "threshold_pace_s_per_km",
    "vo2max",
    "weight_kg",
)
_PENDING_EXISTS = "Ya hay una propuesta pendiente para esta actividad y este protocolo."


def fit_url(activity: Activity) -> str | None:
    """`file.url` del resumen de Wahoo guardado en `raw`, si lo hay."""
    if activity.source != ActivitySource.WAHOO:
        return None
    summary = (activity.raw or {}).get("workout_summary")
    file = summary.get("file") if isinstance(summary, dict) else None
    url = file.get("url") if isinstance(file, dict) else None
    return url if isinstance(url, str) and url else None


def _get_activity(session: Session, user_id: uuid.UUID, activity_id: uuid.UUID) -> Activity:
    activity = session.scalar(
        sa.select(Activity).where(Activity.id == activity_id, Activity.user_id == user_id)
    )
    if activity is None:
        raise NotFoundError("Actividad no encontrada.")
    return activity


def _pending_exists(session: Session, activity_id: uuid.UUID, protocol: ThresholdProtocol) -> bool:
    return bool(
        session.scalar(
            sa.select(sa.literal(True)).where(
                ThresholdProposal.activity_id == activity_id,
                ThresholdProposal.protocol == protocol,
                ThresholdProposal.status == ProposalStatus.PENDING,
            )
        )
    )


def _analyze(data: bytes) -> tuple[datetime, FtpTestResult]:
    """Lee el FIT y analiza el test. Devuelve el instante del primer registro y el resultado."""
    try:
        records = parse_records(data)
    except FitError as exc:
        raise UnprocessableError(str(exc), code="fit_invalid") from exc
    first = records[0].timestamp
    samples = [
        Sample(
            offset_s=(record.timestamp - first).total_seconds(),
            power_w=record.power_w,
            heart_rate_bpm=record.heart_rate_bpm,
        )
        for record in records
    ]
    try:
        result = analyze_ftp_20min(samples)
    except ThresholdTestError as exc:
        raise UnprocessableError(exc.message, code=exc.code) from exc
    return first, result


def _metrics(result: FtpTestResult) -> dict[str, Any]:
    def one_decimal(value: float | None) -> float | None:
        return None if value is None else round(value, 1)

    return {
        "start_offset_s": result.start_offset_s,
        "end_offset_s": result.end_offset_s,
        "duration_s": result.end_offset_s - result.start_offset_s,
        "avg_power_w": one_decimal(result.avg_power_w),
        "normalized_power_w": one_decimal(result.normalized_power_w),
        "variability_index": round(result.variability_index, 3),
        "avg_hr_bpm": one_decimal(result.avg_hr_bpm),
        "max_hr_bpm": one_decimal(result.max_hr_bpm),
        "valid_data_pct": one_decimal(result.valid_data_pct),
        "warmup_s": result.warmup_s,
    }


def create_proposal(
    session: Session,
    user_id: uuid.UUID,
    activity_id: uuid.UUID,
    protocol: ThresholdProtocol,
    fetch_fit: FitFetcher,
) -> ThresholdProposal:
    """Descarga el FIT de la actividad, detecta el test y guarda una propuesta pendiente.

    404 si la actividad no es del atleta; 422 si no es de ciclismo, no tiene FIT o el FIT no
    permite analizar el test; 409 si ya hay una propuesta pendiente de esa actividad. Los
    errores del proveedor al descargar el FIT se propagan (los traduce el router).
    """
    activity = _get_activity(session, user_id, activity_id)
    if activity.sport != Sport.CYCLING:
        raise UnprocessableError(
            "El test de FTP de 20 minutos sólo se analiza en actividades de ciclismo.",
            code="not_cycling",
        )
    url = fit_url(activity)
    if url is None:
        raise UnprocessableError(
            "La actividad no tiene un fichero FIT descargable.", code="fit_unavailable"
        )
    if _pending_exists(session, activity_id, protocol):
        raise ConflictError(_PENDING_EXISTS)
    tz = ZoneInfo(athlete_timezone(session, user_id))
    test_date = activity.start_at.astimezone(tz).date()
    # No se mantiene abierta la transacción de lectura durante la descarga.
    session.rollback()

    first, result = _analyze(fetch_fit(url))
    if not FTP_MIN_W <= result.proposed_ftp_w <= FTP_MAX_W:
        raise UnprocessableError(
            f"El FTP calculado ({result.proposed_ftp_w} W) está fuera del rango admitido"
            f" ({FTP_MIN_W}-{FTP_MAX_W} W).",
            code="ftp_out_of_range",
        )

    proposal = ThresholdProposal(
        user_id=user_id,
        activity_id=activity_id,
        protocol=protocol,
        status=ProposalStatus.PENDING,
        test_date=test_date,
        interval_start_at=(first + timedelta(seconds=result.start_offset_s)).astimezone(UTC),
        interval_end_at=(first + timedelta(seconds=result.end_offset_s)).astimezone(UTC),
        metrics=_metrics(result),
        proposed_ftp_w=result.proposed_ftp_w,
        warnings=[{"code": w.code.value, "message": w.message} for w in result.warnings],
    )
    session.add(proposal)
    try:
        session.flush()
    except IntegrityError as exc:
        # Dos peticiones simultáneas sobre la misma actividad (índice único parcial).
        session.rollback()
        if isinstance(exc.orig, pg_errors.UniqueViolation):
            raise ConflictError(_PENDING_EXISTS) from exc
        raise
    session.commit()
    session.refresh(proposal)
    return proposal


def list_proposals(
    session: Session, user_id: uuid.UUID, status: ProposalStatus | None = None
) -> list[ThresholdProposal]:
    """De la más reciente a la más antigua."""
    query = sa.select(ThresholdProposal).where(ThresholdProposal.user_id == user_id)
    if status is not None:
        query = query.where(ThresholdProposal.status == status)
    return list(
        session.scalars(
            query.order_by(ThresholdProposal.created_at.desc(), ThresholdProposal.id.desc())
        )
    )


def get_proposal(
    session: Session, user_id: uuid.UUID, proposal_id: uuid.UUID, *, for_update: bool = False
) -> ThresholdProposal:
    query = sa.select(ThresholdProposal).where(
        ThresholdProposal.id == proposal_id, ThresholdProposal.user_id == user_id
    )
    if for_update:
        query = query.with_for_update()
    proposal = session.scalar(query)
    if proposal is None:
        raise NotFoundError("Propuesta no encontrada.")
    return proposal


def _pending_for_update(
    session: Session, user_id: uuid.UUID, proposal_id: uuid.UUID
) -> ThresholdProposal:
    proposal = get_proposal(session, user_id, proposal_id, for_update=True)
    if proposal.status != ProposalStatus.PENDING:
        session.rollback()
        raise ConflictError(f"La propuesta ya está {_STATUS_TEXT[proposal.status]}.")
    return proposal


_STATUS_TEXT = {
    ProposalStatus.PENDING: "pendiente",
    ProposalStatus.ACCEPTED: "aceptada",
    ProposalStatus.REJECTED: "rechazada",
}


def threshold_values(proposal: ThresholdProposal, base: AthleteThreshold | None) -> dict[str, Any]:
    """Umbral que se crea al aceptar: el FTP propuesto y el resto copiado del vigente."""
    values: dict[str, Any] = {
        field: None if base is None else getattr(base, field) for field in _COPIED_FIELDS
    }
    values.update(
        effective_from=proposal.test_date,
        ftp_w=proposal.proposed_ftp_w,
        source=ThresholdSource.TEST,
        notes=f"Test de FTP de 20 minutos (propuesta {proposal.id}).",
    )
    return values


def accept_proposal(
    session: Session, user_id: uuid.UUID, proposal_id: uuid.UUID
) -> ThresholdProposal:
    """Crea el umbral nuevo (vigente desde `test_date`) y marca la propuesta como aceptada.

    409 si la propuesta ya no está pendiente o si ya hay umbrales registrados en `test_date`
    (no se sobrescriben: la atleta decide qué hacer con esa fila).
    """
    proposal = _pending_for_update(session, user_id, proposal_id)
    base = thresholds.threshold_on(session, user_id, proposal.test_date)
    threshold = thresholds.add_threshold(session, user_id, threshold_values(proposal, base))
    proposal.status = ProposalStatus.ACCEPTED
    proposal.decided_at = sa.func.now()
    proposal.threshold_id = threshold.id
    session.commit()
    session.refresh(proposal)
    return proposal


def reject_proposal(
    session: Session, user_id: uuid.UUID, proposal_id: uuid.UUID
) -> ThresholdProposal:
    """Marca la propuesta como rechazada. No toca ningún umbral. 409 si no está pendiente."""
    proposal = _pending_for_update(session, user_id, proposal_id)
    proposal.status = ProposalStatus.REJECTED
    proposal.decided_at = sa.func.now()
    session.commit()
    session.refresh(proposal)
    return proposal
