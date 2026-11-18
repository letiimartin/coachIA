"""Propuestas de umbral salidas de un test (#42, #45): analizar, crear, previsualizar, aceptar
y rechazar.

La propuesta no cambia ningún umbral. Al aceptarla, según la vista previa:

- `create_row`: si no hay umbrales en `test_date`, se añade una fila con `source = test`
  (`thresholds.add_threshold`), con el FTP propuesto y el resto copiado del umbral vigente.
- `update_ftp`: si ya hay una fila en `test_date`, sólo se cambia su `ftp_w`
  (`thresholds.update_ftp`); el resto de valores se conservan.

En los dos casos la fila apunta a la propuesta (`ftp_proposal_id`) y los registros posteriores
no se tocan. Sólo corre el gancho normal: rellena la carga de las actividades que no la tienen
y regenera la forma, pero nunca cambia las cargas existentes (protección de #22). **Aceptar
nunca lanza el recálculo histórico** (`scripts/recompute_loads.py`): es otra decisión.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from psycopg import errors as pg_errors
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.integrations.fit import FitError, parse_records
from app.metrics.tests import (
    Comparison,
    FtpTestResult,
    QualityCheck,
    Sample,
    ThresholdProtocol,
    ThresholdTestError,
    analyze_ftp_20min,
)
from app.models import Activity, ActivitySource, AthleteThreshold, Sport, ThresholdProposal
from app.models.athlete import ThresholdSource
from app.models.threshold_proposal import AcceptAction, PreviewWarningCode, ProposalStatus
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


def check_out(check: QualityCheck) -> dict[str, Any]:
    """Criterio evaluado tal como lo ve el cliente (avisos, `checks` y `error.details`)."""
    return {
        "code": check.criterion.value,
        "passed": check.passed,
        "blocking": check.blocking,
        "measured": check.measured,
        "threshold": check.threshold,
        "comparison": check.comparison.value,
        "unit": check.unit,
        "message": check.message,
    }


def _analyze(data: bytes) -> tuple[datetime, FtpTestResult]:
    """Lee el FIT y analiza el test. Devuelve el instante del primer registro y el resultado.

    Si falla un criterio bloqueante, 422 con su `code` y el criterio en `error.details`.
    """
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
        raise UnprocessableError(exc.message, code=exc.code, details=check_out(exc.check)) from exc
    _check_ftp_range(result.proposed_ftp_w)
    return first, result


def _check_ftp_range(ftp_w: int) -> None:
    """422 `ftp_out_of_range` (con el detalle del límite) si el FTP no es admisible."""
    if FTP_MIN_W <= ftp_w <= FTP_MAX_W:
        return
    limit, comparison = (
        (FTP_MIN_W, Comparison.GE) if ftp_w < FTP_MIN_W else (FTP_MAX_W, Comparison.LE)
    )
    message = (
        f"El FTP calculado ({ftp_w} W) está fuera del rango admitido ({FTP_MIN_W}-{FTP_MAX_W} W)."
    )
    details = {
        "code": "ftp_out_of_range",
        "passed": False,
        "blocking": True,
        "measured": ftp_w,
        "threshold": limit,
        "comparison": comparison.value,
        "unit": "W",
        "message": message,
    }
    raise UnprocessableError(message, code="ftp_out_of_range", details=details)


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


@dataclass(frozen=True, slots=True)
class TestAnalysis:
    """Resultado del análisis de una actividad, guardado o no como propuesta."""

    __test__ = False  # No es un test de pytest.

    activity_id: uuid.UUID
    protocol: ThresholdProtocol
    test_date: date
    interval_start_at: datetime
    interval_end_at: datetime
    metrics: dict[str, Any]
    proposed_ftp_w: int
    checks: list[dict[str, Any]]
    warnings: list[dict[str, Any]]


def _test_activity(
    session: Session, user_id: uuid.UUID, activity_id: uuid.UUID
) -> tuple[str, date]:
    """URL del FIT y día local de la actividad. 404 si no es del atleta; 422 si no es de
    ciclismo o no tiene FIT."""
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
    tz = ZoneInfo(athlete_timezone(session, user_id))
    return url, activity.start_at.astimezone(tz).date()


def _run_analysis(
    session: Session,
    activity_id: uuid.UUID,
    protocol: ThresholdProtocol,
    url: str,
    test_date: date,
    fetch_fit: FitFetcher,
) -> TestAnalysis:
    # No se mantiene abierta la transacción de lectura durante la descarga.
    session.rollback()

    first, result = _analyze(fetch_fit(url))
    return TestAnalysis(
        activity_id=activity_id,
        protocol=protocol,
        test_date=test_date,
        interval_start_at=(first + timedelta(seconds=result.start_offset_s)).astimezone(UTC),
        interval_end_at=(first + timedelta(seconds=result.end_offset_s)).astimezone(UTC),
        metrics=_metrics(result),
        proposed_ftp_w=result.proposed_ftp_w,
        checks=[check_out(check) for check in result.checks],
        warnings=[check_out(check) for check in result.warnings],
    )


def analyze_activity(
    session: Session,
    user_id: uuid.UUID,
    activity_id: uuid.UUID,
    protocol: ThresholdProtocol,
    fetch_fit: FitFetcher,
) -> TestAnalysis:
    """Análisis de prueba (`dry-run`): descarga el FIT y analiza el test **sin guardar nada**.

    Mismos errores que `create_proposal`, salvo el 409 de propuesta pendiente (no se crea).
    """
    url, test_date = _test_activity(session, user_id, activity_id)
    return _run_analysis(session, activity_id, protocol, url, test_date, fetch_fit)


def create_proposal(
    session: Session,
    user_id: uuid.UUID,
    activity_id: uuid.UUID,
    protocol: ThresholdProtocol,
    fetch_fit: FitFetcher,
) -> ThresholdProposal:
    """Descarga el FIT de la actividad, detecta el test y guarda una propuesta pendiente.

    404 si la actividad no es del atleta; 422 si no es de ciclismo, no tiene FIT o el FIT no
    permite analizar el test (con el criterio que falla en `error.details`); 409 si ya hay una
    propuesta pendiente de esa actividad. Los errores del proveedor al descargar el FIT se
    propagan (los traduce el router).
    """
    url, test_date = _test_activity(session, user_id, activity_id)
    if _pending_exists(session, activity_id, protocol):
        raise ConflictError(_PENDING_EXISTS)
    analysis = _run_analysis(session, activity_id, protocol, url, test_date, fetch_fit)

    proposal = ThresholdProposal(
        user_id=user_id,
        activity_id=activity_id,
        protocol=protocol,
        status=ProposalStatus.PENDING,
        test_date=analysis.test_date,
        interval_start_at=analysis.interval_start_at,
        interval_end_at=analysis.interval_end_at,
        metrics=analysis.metrics,
        proposed_ftp_w=analysis.proposed_ftp_w,
        warnings=analysis.warnings,
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
    """Fila que crea `create_row`: el FTP propuesto y el resto copiado del umbral vigente."""
    values: dict[str, Any] = {
        field: None if base is None else getattr(base, field) for field in _COPIED_FIELDS
    }
    values.update(
        effective_from=proposal.test_date,
        ftp_w=proposal.proposed_ftp_w,
        source=ThresholdSource.TEST,
        notes=f"Test de FTP de 20 minutos (propuesta {proposal.id}).",
        ftp_proposal_id=proposal.id,
    )
    return values


@dataclass(frozen=True, slots=True)
class NextThreshold:
    id: uuid.UUID
    effective_from: date
    ftp_w: int | None


@dataclass(frozen=True, slots=True)
class PreviewWarning:
    code: PreviewWarningCode
    message: str


@dataclass(frozen=True, slots=True)
class AcceptancePreview:
    """Qué haría aceptar la propuesta con los umbrales actuales. Ver `AcceptancePreviewOut`."""

    proposal_id: uuid.UUID
    action: AcceptAction
    threshold_id: uuid.UUID | None
    previous_ftp_w: int | None
    proposed_ftp_w: int
    effective_from: date
    effective_until: date | None
    next_threshold: NextThreshold | None
    warnings: list[PreviewWarning]


@dataclass(frozen=True, slots=True)
class _Plan:
    preview: AcceptancePreview
    # Umbral vigente en `test_date` (la fila de esa fecha si la hay) y la fila de esa fecha.
    base: AthleteThreshold | None
    row_on_date: AthleteThreshold | None


def _plan(
    session: Session, user_id: uuid.UUID, proposal: ThresholdProposal, *, lock: bool = False
) -> _Plan:
    """Calcula la vista previa. Con `lock`, bloquea la fila vigente en `test_date` hasta el commit."""
    test_date = proposal.test_date
    base_query = (
        sa.select(AthleteThreshold)
        .where(AthleteThreshold.user_id == user_id, AthleteThreshold.effective_from <= test_date)
        .order_by(AthleteThreshold.effective_from.desc())
        .limit(1)
    )
    if lock:
        base_query = base_query.with_for_update()
    base = session.scalar(base_query)
    following = session.scalar(
        sa.select(AthleteThreshold)
        .where(AthleteThreshold.user_id == user_id, AthleteThreshold.effective_from > test_date)
        .order_by(AthleteThreshold.effective_from)
        .limit(1)
    )
    row_on_date = base if base is not None and base.effective_from == test_date else None

    warnings: list[PreviewWarning] = []
    next_threshold = None
    effective_until = None
    if following is not None:
        next_threshold = NextThreshold(following.id, following.effective_from, following.ftp_w)
        effective_until = following.effective_from - timedelta(days=1)
        ftp_after = "sin FTP" if following.ftp_w is None else f"{following.ftp_w} W"
        warnings.append(
            PreviewWarning(
                PreviewWarningCode.LATER_THRESHOLDS,
                f"Hay umbrales registrados desde el {following.effective_from.isoformat()}: el"
                f" FTP nuevo sólo regirá hasta el {effective_until.isoformat()} y después"
                f" seguirá vigente el de ese registro ({ftp_after}). Los registros posteriores"
                " no se modifican.",
            )
        )
    preview = AcceptancePreview(
        proposal_id=proposal.id,
        action=AcceptAction.CREATE_ROW if row_on_date is None else AcceptAction.UPDATE_FTP,
        threshold_id=None if row_on_date is None else row_on_date.id,
        previous_ftp_w=None if base is None else base.ftp_w,
        proposed_ftp_w=proposal.proposed_ftp_w,
        effective_from=test_date,
        effective_until=effective_until,
        next_threshold=next_threshold,
        warnings=warnings,
    )
    return _Plan(preview=preview, base=base, row_on_date=row_on_date)


def preview_acceptance(
    session: Session, user_id: uuid.UUID, proposal_id: uuid.UUID
) -> AcceptancePreview:
    """Vista previa de aceptar la propuesta. No guarda nada. 409 si no está pendiente."""
    proposal = get_proposal(session, user_id, proposal_id)
    if proposal.status != ProposalStatus.PENDING:
        raise ConflictError(f"La propuesta ya está {_STATUS_TEXT[proposal.status]}.")
    return _plan(session, user_id, proposal).preview


def accept_proposal(
    session: Session,
    user_id: uuid.UUID,
    proposal_id: uuid.UUID,
    action: AcceptAction,
    previous_ftp_w: int | None,
) -> ThresholdProposal:
    """Aplica la propuesta tal como la mostró la vista previa y la marca como aceptada.

    `action` y `previous_ftp_w` son los de la vista previa que vio la atleta: si ya no
    coinciden (los umbrales cambiaron entretanto), 409 `preview_outdated` con la vista previa
    nueva en `error.details` y no se guarda nada. 409 también si la propuesta ya no está
    pendiente. No lanza ningún recálculo histórico.
    """
    proposal = _pending_for_update(session, user_id, proposal_id)
    plan = _plan(session, user_id, proposal, lock=True)
    preview = plan.preview
    if (preview.action, preview.previous_ftp_w) != (action, previous_ftp_w):
        session.rollback()
        raise ConflictError(
            "Los umbrales han cambiado desde la vista previa: revisa la nueva antes de aceptar.",
            code="preview_outdated",
            details=preview,
        )
    if plan.row_on_date is None:
        threshold = thresholds.add_threshold(
            session, user_id, threshold_values(proposal, plan.base)
        )
    else:
        threshold = thresholds.update_ftp(
            session, user_id, plan.row_on_date, proposal.proposed_ftp_w, proposal.id
        )
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
