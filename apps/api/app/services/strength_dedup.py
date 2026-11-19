"""Deduplicación de sesiones de fuerza: la registrada en la app y la grabada por Wahoo (#32).

Criterio aprobado por la autora (comentario del 19 nov en #32):

- Candidatas: las dos son de fuerza (`sport = strength`), del mismo atleta y del mismo día local
  (zona horaria del atleta). Una es de la app (`source = manual`) y la otra de un dispositivo
  (`DEVICE_SOURCES`, de momento sólo Wahoo).
- Tolerancias: el inicio puede diferir hasta 30 minutos y la duración hasta un 20 % de la
  registrada en la app.
- Enlace sólo si la coincidencia es única por los dos lados: la del dispositivo tiene una sola
  candidata de la app y esa sesión de la app tiene una sola candidata del dispositivo. Si falta
  el inicio o la duración de alguna, o hay varias coincidencias, quedan separadas.
- La sesión de la app es la principal: conserva las series, los pesos y el RPE. La del
  dispositivo se enlaza con `duplicate_of_id` (no suma nunca en la carga diaria) y de ella se
  copian a la principal la duración y la FC, cuando son válidas.

Al copiar la duración, la carga `session_rpe` de la principal (minutos × RPE) se vacía para que
el recálculo normal la vuelva a calcular con la duración nueva. No depende de umbrales, así que
no la afecta la protección de cargas de #22. Los valores que la atleta registró en la app se
guardan en `raw["app_recorded"]` la primera vez, y la comparación usa siempre esa duración.

Si el dispositivo actualiza una sesión ya enlazada (p. ej. la editan en Wahoo), la duración y la
FC se vuelven a copiar. Un enlace nunca se deshace solo. No hace commit: lo hace quien llama,
que también recalcula la carga y la forma (`services.fitness`) desde el día afectado.
"""

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models import Activity, ActivitySource, LoadMethod, Sport
from app.services.athletes import athlete_timezone

DEVICE_SOURCES: tuple[ActivitySource, ...] = (ActivitySource.WAHOO,)
START_TOLERANCE = timedelta(minutes=30)
DURATION_TOLERANCE = 0.20
# FC media o máxima que se acepta como válida (lpm). Fuera de este rango es un error de sensor.
MIN_VALID_HR = 25
MAX_VALID_HR = 250
APP_RECORDED_KEY = "app_recorded"
# Lo que se copia del dispositivo a la sesión de la app.
_RECORDED_FIELDS = ("elapsed_s", "moving_s", "avg_hr", "max_hr")


def _local_day(moment: datetime, tz: ZoneInfo) -> date:
    return moment.astimezone(tz).date()


def _positive(value: int | None) -> int | None:
    return value if value is not None and value > 0 else None


def app_duration_s(activity: Activity) -> int | None:
    """Duración registrada en la app (antes de copiar la del dispositivo)."""
    recorded = (activity.raw or {}).get(APP_RECORDED_KEY)
    if isinstance(recorded, dict):
        elapsed, moving = recorded.get("elapsed_s"), recorded.get("moving_s")
    else:
        elapsed, moving = activity.elapsed_s, activity.moving_s
    return _positive(elapsed) or _positive(moving)


def device_duration_s(activity: Activity) -> int | None:
    """Duración total de la sesión grabada (la de la app también es total, con descansos)."""
    return _positive(activity.elapsed_s) or _positive(activity.moving_s)


def _valid_hr(value: int | None) -> int | None:
    return value if value is not None and MIN_VALID_HR <= value <= MAX_VALID_HR else None


def is_match(app: Activity, device: Activity, tz: ZoneInfo) -> bool:
    """Si las dos actividades cumplen el criterio de misma sesión. Pura, sin BD."""
    if app.user_id != device.user_id:
        return False
    if app.sport != Sport.STRENGTH or device.sport != Sport.STRENGTH:
        return False
    if app.source != ActivitySource.MANUAL or device.source not in DEVICE_SOURCES:
        return False
    if app.start_at is None or device.start_at is None:
        return False
    if _local_day(app.start_at, tz) != _local_day(device.start_at, tz):
        return False
    if abs(app.start_at - device.start_at) > START_TOLERANCE:
        return False
    app_s, device_s = app_duration_s(app), device_duration_s(device)
    if app_s is None or device_s is None:
        return False
    return abs(device_s - app_s) <= DURATION_TOLERANCE * app_s


def match_pairs(
    apps: Sequence[Activity], devices: Sequence[Activity], tz: ZoneInfo
) -> list[tuple[Activity, Activity]]:
    """Parejas (app, dispositivo) con una única coincidencia clara por los dos lados. Pura."""
    candidates = {
        id(device): [app for app in apps if is_match(app, device, tz)] for device in devices
    }
    pairs: list[tuple[Activity, Activity]] = []
    for device in devices:
        matches = candidates[id(device)]
        if len(matches) != 1:
            continue
        app = matches[0]
        rivals = [other for other in devices if any(m is app for m in candidates[id(other)])]
        if len(rivals) == 1:
            pairs.append((app, device))
    return pairs


def apply_device_metrics(app: Activity, device: Activity) -> bool:
    """Copia a la sesión de la app la duración y la FC válidas del dispositivo.

    Guarda antes lo registrado en la app (una sola vez). Si cambia la duración, vacía la carga
    `session_rpe` para que el recálculo la rehaga. Devuelve si cambió algo.
    """
    raw: dict[str, Any] = dict(app.raw or {})
    if APP_RECORDED_KEY not in raw:
        raw[APP_RECORDED_KEY] = {name: getattr(app, name) for name in _RECORDED_FIELDS}
        app.raw = raw

    new_values: dict[str, int] = {}
    duration = device_duration_s(device)
    if duration is not None:
        new_values["elapsed_s"] = duration
        new_values["moving_s"] = duration
    for name in ("avg_hr", "max_hr"):
        hr = _valid_hr(getattr(device, name))
        if hr is not None:
            new_values[name] = hr

    changed = {name for name, value in new_values.items() if getattr(app, name) != value}
    for name in changed:
        setattr(app, name, new_values[name])
    if changed & {"elapsed_s", "moving_s"} and app.load_method in (None, LoadMethod.SESSION_RPE):
        app.load = app.load_method = app.intensity_factor = None
    return bool(changed)


@dataclass(frozen=True, slots=True)
class DedupResult:
    linked: int = 0
    refreshed: int = 0


def _lock_athlete(session: Session, user_id: uuid.UUID) -> None:
    """Serializa la deduplicación del mismo atleta (sync y completar a la vez) hasta el commit."""
    session.execute(
        sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(f"strength_dedup:{user_id}")))
    )


def link_strength_sessions(
    session: Session, user_id: uuid.UUID, moments: Iterable[datetime]
) -> DedupResult:
    """Enlaza las sesiones de fuerza duplicadas de los días locales de `moments`.

    También vuelve a copiar la duración y la FC de los enlaces que ya existían esos días. Sin
    commit; quien llama recalcula la forma desde el día más antiguo.
    """
    tz = ZoneInfo(athlete_timezone(session, user_id))
    days = sorted({_local_day(moment, tz) for moment in moments})
    if not days:
        return DedupResult()
    _lock_athlete(session, user_id)
    session.flush()
    linked = refreshed = 0
    for day in days:
        start = datetime.combine(day, time.min, tzinfo=tz)
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
        rows = session.scalars(
            sa.select(Activity)
            .where(
                Activity.user_id == user_id,
                Activity.sport == Sport.STRENGTH,
                Activity.source.in_((ActivitySource.MANUAL, *DEVICE_SOURCES)),
                Activity.start_at >= start,
                Activity.start_at < end,
            )
            .order_by(Activity.start_at, Activity.id)
            # El sync escribe con INSERT ... ON CONFLICT: que no se usen copias viejas en memoria.
            .execution_options(populate_existing=True)
        ).all()
        apps = [row for row in rows if row.source == ActivitySource.MANUAL]
        devices = [row for row in rows if row.source in DEVICE_SOURCES]
        by_id = {app.id: app for app in apps}

        # Enlaces existentes: se refrescan y quedan fuera de las candidatas.
        taken: set[uuid.UUID] = set()
        for device in devices:
            if device.duplicate_of_id is None:
                continue
            taken.add(device.duplicate_of_id)
            principal = by_id.get(device.duplicate_of_id)
            if principal is not None and apply_device_metrics(principal, device):
                refreshed += 1
        taken |= set(
            session.scalars(
                sa.select(Activity.duplicate_of_id).where(
                    Activity.duplicate_of_id.in_([app.id for app in apps])
                )
            )
        )
        free_apps = [app for app in apps if app.id not in taken]
        free_devices = [device for device in devices if device.duplicate_of_id is None]
        for app, device in match_pairs(free_apps, free_devices, tz):
            device.duplicate_of_id = app.id
            apply_device_metrics(app, device)
            linked += 1
    session.flush()
    return DedupResult(linked=linked, refreshed=refreshed)
