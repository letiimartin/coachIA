"""Sincronización de actividades de Wahoo en `activities` (idempotente).

- Recorre `GET /v1/workouts` (ordenado por `starts` descendente) página a página.
- Sólo importa workouts con resumen (los realizados); los planificados no tienen resumen.
- Upsert por (user_id, source='wahoo', external_id=id del workout). Una fila existente sólo se
  reescribe si cambia la respuesta de Wahoo (`raw`), así que repetir el sync no modifica nada.
- `integrations.sync_cursor` guarda el inicio más reciente importado. Los syncs siguientes paran
  al llegar a workouts que empezaron antes de ese inicio menos un margen (`INCREMENTAL_OVERLAP`),
  para recoger también workouts subidos o editados con retraso.
- Al terminar, recalcula la carga y la forma (`services.fitness.recompute_from`) desde el día
  de la actividad más antigua creada o modificada (backfill incluido); si no cambió nada, sólo
  completa la serie hasta hoy.
- 401/403 de Wahoo → la integración pasa a `error` (hay que reconectar). Límites (429), red o
  5xx son transitorios: se guarda `last_error` sin cambiar el estado y el cursor no avanza.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.crypto import TokenCipher
from app.integrations.wahoo import service
from app.integrations.wahoo.client import (
    WahooApiError,
    WahooClient,
    WahooNotFoundError,
    WahooRateLimitError,
    WahooUnauthorizedError,
)
from app.integrations.wahoo.mapper import (
    MappedActivity,
    WahooMappingError,
    map_workout,
    parse_datetime,
)
from app.models import Activity, ActivitySource, Integration, IntegrationStatus, Provider
from app.services import fitness

logger = logging.getLogger(__name__)

INCREMENTAL_OVERLAP = timedelta(days=7)
# Tope de seguridad por ejecución (con 50 por página, 10 000 workouts).
MAX_PAGES = 200
CURSOR_KEY = "latest_start_at"

UpsertOutcome = Literal["created", "updated", "unchanged"]


@dataclass
class SyncResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0

    def add(self, outcome: UpsertOutcome) -> None:
        setattr(self, outcome, getattr(self, outcome) + 1)


@dataclass
class SyncAllResult:
    integrations: int = 0
    succeeded: int = 0
    failed: int = 0
    rate_limited: bool = False
    totals: SyncResult = field(default_factory=SyncResult)


def _now() -> datetime:
    return datetime.now(UTC)


def sync_user(
    session: Session, cipher: TokenCipher, client: WahooClient, user_id: uuid.UUID
) -> SyncResult:
    """Importa los workouts de Wahoo del usuario.

    Lanza service.WahooNotConnectedError si no hay integración utilizable y las excepciones de
    WahooApiError si Wahoo falla (tras dejar la integración en el estado que corresponde).
    """
    access_token = service.get_valid_access_token(session, cipher, client, user_id)
    integration = service.get_integration(session, user_id)
    if integration is None:  # pragma: no cover - get_valid_access_token ya lo comprueba
        raise service.WahooNotConnectedError()

    previous_latest = _parse_cursor(integration.sync_cursor)
    stop_before = previous_latest - INCREMENTAL_OVERLAP if previous_latest else None
    result = SyncResult()
    latest = previous_latest
    earliest_changed: datetime | None = None

    try:
        page = 1
        while True:
            workouts_page = client.list_workouts(access_token, page=page)
            reached_known = False
            for workout in workouts_page.workouts:
                starts = parse_datetime(workout.get("starts"))
                if stop_before is not None and starts is not None and starts < stop_before:
                    reached_known = True
                    break
                summary = _summary_for(client, access_token, workout)
                if summary is None:
                    continue  # Planificado o sin resultados todavía.
                try:
                    mapped = map_workout(workout, summary)
                except WahooMappingError as exc:
                    logger.warning("Workout de Wahoo omitido: %s", exc)
                    continue
                outcome = _upsert(session, user_id, mapped)
                result.add(outcome)
                start_at: datetime = mapped.values["start_at"]
                if outcome != "unchanged" and (
                    earliest_changed is None or start_at < earliest_changed
                ):
                    earliest_changed = start_at
                latest = start_at if latest is None else max(latest, start_at)
            session.commit()  # Lo importado se conserva aunque falle una página posterior.

            fetched = page * workouts_page.per_page
            if reached_known or not workouts_page.workouts or fetched >= workouts_page.total:
                break
            if page >= MAX_PAGES:
                logger.warning("Sync de Wahoo cortado en %s páginas (usuario %s)", page, user_id)
                break
            page += 1
    except WahooUnauthorizedError as exc:
        session.rollback()
        _record_error(session, integration, str(exc), status=IntegrationStatus.ERROR)
        raise
    except WahooApiError as exc:
        session.rollback()
        _record_error(session, integration, str(exc), status=None)
        raise

    if earliest_changed is not None:
        fitness.recompute_since_activity(session, user_id, earliest_changed)
    else:
        fitness.extend_to_today(session, user_id)
    integration.last_sync_at = _now()
    integration.last_error = None
    if latest is not None:
        integration.sync_cursor = {**integration.sync_cursor, CURSOR_KEY: latest.isoformat()}
    session.commit()
    logger.info(
        "Sync de Wahoo del usuario %s: %s creadas, %s actualizadas, %s sin cambios",
        user_id,
        result.created,
        result.updated,
        result.unchanged,
    )
    return result


def sync_all(session: Session, cipher: TokenCipher, client: WahooClient) -> SyncAllResult:
    """Sincroniza todas las integraciones de Wahoo activas (para la automatización de n8n).

    Un fallo de un usuario no detiene a los demás, salvo el límite de peticiones (429), que es
    por aplicación: en ese caso se para y el resto se sincronizará en la próxima ejecución.
    """
    user_ids = session.scalars(
        select(Integration.user_id)
        .where(
            Integration.provider == Provider.WAHOO,
            Integration.status == IntegrationStatus.ACTIVE,
        )
        .order_by(Integration.last_sync_at.asc().nulls_first())
    ).all()
    outcome = SyncAllResult(integrations=len(user_ids))
    for user_id in user_ids:
        try:
            result = sync_user(session, cipher, client, user_id)
        except WahooRateLimitError:
            outcome.failed += 1
            outcome.rate_limited = True
            break
        except (service.WahooNotConnectedError, WahooApiError) as exc:
            logger.warning("Sync de Wahoo fallido para el usuario %s: %s", user_id, exc)
            session.rollback()
            outcome.failed += 1
            continue
        outcome.succeeded += 1
        outcome.totals.created += result.created
        outcome.totals.updated += result.updated
        outcome.totals.unchanged += result.unchanged
    return outcome


def _summary_for(
    client: WahooClient, access_token: str, workout: dict[str, Any]
) -> dict[str, Any] | None:
    """Resumen del workout: el incluido en el listado o, si no viene, el del endpoint propio."""
    if "workout_summary" in workout:
        summary = workout["workout_summary"]
    else:
        workout_id = workout.get("id")
        if workout_id is None:
            return None
        try:
            summary = client.get_workout_summary(access_token, workout_id)
        except WahooNotFoundError:
            return None
    return summary if isinstance(summary, dict) and summary else None


def _upsert(session: Session, user_id: uuid.UUID, mapped: MappedActivity) -> UpsertOutcome:
    statement = insert(Activity).values(
        user_id=user_id,
        source=ActivitySource.WAHOO,
        external_id=mapped.external_id,
        **mapped.values,
    )
    upsert: Any = statement.on_conflict_do_update(
        index_elements=[Activity.user_id, Activity.source, Activity.external_id],
        set_={
            **{name: statement.excluded[name] for name in mapped.values},
            "updated_at": sa.func.now(),
        },
        # Sin cambios en la respuesta de Wahoo no se reescribe la fila.
        where=Activity.raw.is_distinct_from(statement.excluded.raw),
    ).returning(sa.literal_column("xmax = 0").label("inserted"))
    row = session.execute(upsert).first()
    if row is None:
        return "unchanged"
    return "created" if row.inserted else "updated"


def _record_error(
    session: Session,
    integration: Integration,
    message: str,
    *,
    status: IntegrationStatus | None,
) -> None:
    logger.warning("Sync de Wahoo de la integración %s: %s", integration.id, message)
    if status is not None:
        integration.status = status
    integration.last_error = message
    session.commit()


def _parse_cursor(cursor: dict[str, Any] | None) -> datetime | None:
    return parse_datetime((cursor or {}).get(CURSOR_KEY))
