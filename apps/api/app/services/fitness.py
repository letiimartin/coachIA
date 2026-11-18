"""Carga de las actividades y serie diaria de forma (CTL/ATL/TSB) en `daily_load` (#17).

Un único punto de entrada para recalcular: `recompute_from(session, user_id, since)`. Recalcula
la carga de las actividades desde `since` (con el umbral vigente en la fecha de cada una) y
regenera `daily_load` desde ese día hasta hoy, porque CTL y ATL dependen de toda la serie
anterior. Es idempotente: repetirlo con los mismos datos deja las mismas filas. Lo llaman todos
los ganchos (sync de actividades, umbral nuevo y, cuando existan, edición o borrado de
actividades). No hace commit: lo hace quien llama.

Criterios:
- El día de una actividad es el local en la zona horaria del atleta.
- Duración: `moving_s` en los métodos TSS (sin ella no hay carga; no se inventa). La fuerza usa
  `moving_s` o, si no hay, `elapsed_s`.
- El método de carga va por deporte (`app.metrics.load.LOAD_RULES`) y el LTHR de cada deporte
  sale de `app.metrics.zones.lthr_field_for`.
- La carga diaria sólo suma resistencia (`counts_in_daily_load`). La fuerza (`strength`) se
  calcula por `session_rpe` y esa carga no suma nunca.
- Senderismo, natación y otros sólo se registran: no se les calcula carga y las que ya tienen
  se conservan siempre como dato histórico (tampoco el recálculo explícito las borra).
- Carga histórica (`_is_historical_load`): la carga TSS calculada antes de #22 para deportes que
  ahora no suman (senderismo, natación, otros y el TSS por FC de la fuerza). Mientras dure la
  protección, sigue contando en la curva, para que no cambie antes de que la autora apruebe el
  recálculo; el recálculo explícito la excluye (y en la fuerza la sustituye por `session_rpe` o
  la deja vacía), y `simulate_curve` enseña cuánto cambia la curva al excluirla.
- Las actividades marcadas como duplicadas (`duplicate_of_id`) tienen su carga, pero no suman
  en la carga diaria. Las de carga por RPE (manual) no se recalculan.

Protección de las cargas existentes (#22): los recálculos automáticos (sync, umbral nuevo) sólo
calculan la carga de las actividades que no la tienen; nunca borran ni cambian una que ya
existe, aunque ahora no se pudiera calcular. Cambiar cargas existentes es el recálculo histórico
explícito (`recompute_from(..., overwrite_existing=True)`, vía `scripts/recompute_loads.py`),
que tiene modos de simulación (`simulate_recompute`, `simulate_curve`) que no escriben nada.

La protección se levanta con `AUTOMATIC_RECOMPUTE_OVERWRITES`. Al aprobarlo, primero se
despliega con True y después se ejecuta el recálculo explícito, para que ningún gancho
automático vuelva a meter en la curva lo que el recálculo excluye.
"""

import bisect
import logging
import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.metrics.fitness import FitnessDay, fitness_series
from app.metrics.load import LOAD_RULES, LoadResult, activity_load, counts_in_daily_load
from app.metrics.zones import lthr_field_for
from app.models import Activity, AthleteThreshold, DailyLoad, LoadMethod
from app.services.athletes import athlete_timezone, today_for

logger = logging.getLogger(__name__)

# Hasta que la autora valide los umbrales por disciplina (#22), los procesos automáticos no
# cambian cargas existentes. Para levantar la protección basta con poner esto a True.
AUTOMATIC_RECOMPUTE_OVERWRITES = False

# Límites de las columnas: activities.load Numeric(6,1) e intensity_factor Numeric(4,3).
_MAX_ACTIVITY_LOAD = Decimal("99999.9")
_MAX_INTENSITY_FACTOR = Decimal("9.999")

_ONE = Decimal("0.1")
_THREE = Decimal("0.001")


def _quantize(value: float, step: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(step, rounding=ROUND_HALF_UP)


# --- Carga de una actividad ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Thresholds:
    """Umbrales ordenados por `effective_from` para buscar el vigente en una fecha."""

    days: list[date]
    rows: list[AthleteThreshold]

    @classmethod
    def load(cls, session: Session, user_id: uuid.UUID) -> "_Thresholds":
        rows = list(
            session.scalars(
                sa.select(AthleteThreshold)
                .where(AthleteThreshold.user_id == user_id)
                .order_by(AthleteThreshold.effective_from)
            )
        )
        return cls([row.effective_from for row in rows], rows)

    def on(self, day: date) -> AthleteThreshold | None:
        index = bisect.bisect_right(self.days, day)
        return self.rows[index - 1] if index else None


def _float(value: Decimal | int | None) -> float | None:
    return None if value is None else float(value)


def compute_activity_load(
    activity: Activity, threshold: AthleteThreshold | None
) -> LoadResult | None:
    """Carga de la actividad con el umbral dado (el vigente en su fecha). Pura, sin BD.

    Las cargas por RPE (manuales) no se calculan aquí: quien llama las conserva.
    """
    sport = activity.sport

    def limit(name: str | None) -> float | None:
        if threshold is None or name is None:
            return None
        return _float(getattr(threshold, name))

    return activity_load(
        sport,
        _float(activity.moving_s),
        elapsed_s=_float(activity.elapsed_s),
        normalized_power_w=_float(activity.normalized_power_w),
        ftp_w=limit("ftp_w"),
        avg_hr_bpm=_float(activity.avg_hr),
        lthr_bpm=limit(lthr_field_for(sport)),
        avg_speed_mps=_float(activity.avg_speed_mps),
        threshold_pace_s_per_km=limit("threshold_pace_s_per_km"),
        rpe=activity.rpe,
    )


_StoredLoad = tuple[Decimal | None, LoadMethod | None, Decimal | None]


def _stored_values(activity: Activity, result: LoadResult | None) -> _StoredLoad:
    """Valores tal como se guardarían en `activities` (redondeados y acotados)."""
    load = method = intensity = None
    if result is not None:
        load = _quantize(result.load, _ONE)
        intensity = (
            None if result.intensity_factor is None else _quantize(result.intensity_factor, _THREE)
        )
        method = result.method
        if load > _MAX_ACTIVITY_LOAD or (
            intensity is not None and intensity > _MAX_INTENSITY_FACTOR
        ):
            # Datos absurdos (p. ej. NP muy por encima del FTP): no se guarda una carga falsa.
            logger.warning("Carga fuera de rango en la actividad %s; se deja vacía", activity.id)
            load = method = intensity = None
    return load, method, intensity


def _current(activity: Activity) -> _StoredLoad:
    return activity.load, activity.load_method, activity.intensity_factor


def _keeps_current_load(activity: Activity, *, overwrite_existing: bool) -> bool:
    """RPE (manual) nunca se recalcula; una carga existente sólo con `overwrite_existing`.

    La carga histórica de un deporte que sólo se registra no se recalcula nunca: es el dato
    que había y no hay método para sustituirla.
    """
    if activity.load_method == LoadMethod.RPE:
        return True
    if activity.load is not None and LOAD_RULES[activity.sport].registered_only:
        return True
    return activity.load is not None and not overwrite_existing


def _is_historical_load(activity: Activity) -> bool:
    """Carga TSS anterior a #22 de un deporte que ahora no suma en CTL/ATL.

    Es la de senderismo, natación y otros, y el TSS (por FC) de la fuerza. Nunca la carga
    `session_rpe`, que es de fuerza y no suma nunca.
    """
    return (
        activity.load is not None
        and not LOAD_RULES[activity.sport].endurance
        and activity.load_method is not LoadMethod.SESSION_RPE
    )


def _counts_in_curve(activity: Activity, *, overwrite_existing: bool) -> bool:
    """Si la carga guardada de la actividad suma en `daily_load`.

    Con protección (`overwrite_existing` False), la carga histórica (`_is_historical_load`) sigue
    sumando como antes; el recálculo explícito la excluye.
    """
    if activity.duplicate_of_id is not None or activity.load is None:
        return False
    if counts_in_daily_load(activity.sport, activity.load_method):
        return True
    return not overwrite_existing and _is_historical_load(activity)


def _apply_load(activity: Activity, result: LoadResult | None) -> None:
    new = _stored_values(activity, result)
    if _current(activity) != new:
        activity.load, activity.load_method, activity.intensity_factor = new


# --- Recálculo -------------------------------------------------------------------------------


def _local_day(moment: datetime, tz: ZoneInfo) -> date:
    return moment.astimezone(tz).date()


def _start_of(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz)


def _lock_athlete(session: Session, user_id: uuid.UUID) -> None:
    """Serializa los recálculos del mismo atleta (sync y umbral a la vez) hasta el commit."""
    session.execute(
        sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(f"daily_load:{user_id}")))
    )


def recompute_from(
    session: Session,
    user_id: uuid.UUID,
    since: date,
    *,
    today: date | None = None,
    overwrite_existing: bool | None = None,
) -> None:
    """Recalcula la carga de las actividades desde `since` y regenera `daily_load`.

    `overwrite_existing` decide si se recalculan también las actividades que ya tienen carga.
    Por defecto (`None`) vale `AUTOMATIC_RECOMPUTE_OVERWRITES`: los ganchos automáticos sólo
    rellenan las que no la tienen. El recálculo histórico explícito pasa `True`.

    Si no hay serie guardada justo antes de `since` (primera vez, o un hueco), empieza antes:
    en el día siguiente a la última fila guardada o, si no hay ninguna, en la primera actividad.
    Si `since` es anterior a la primera actividad, la serie se regenera entera. Sin commit.
    """
    if overwrite_existing is None:
        overwrite_existing = AUTOMATIC_RECOMPUTE_OVERWRITES
    _lock_athlete(session, user_id)
    tz = ZoneInfo(athlete_timezone(session, user_id))
    today = today or datetime.now(tz).date()

    bounds = session.execute(
        sa.select(sa.func.min(Activity.start_at), sa.func.max(Activity.start_at)).where(
            Activity.user_id == user_id
        )
    ).one()
    if bounds[0] is None:
        session.execute(sa.delete(DailyLoad).where(DailyLoad.user_id == user_id))
        return
    first_day = _local_day(bounds[0], tz)
    end = max(today, _local_day(bounds[1], tz))

    start, initial_ctl, initial_atl = first_day, 0.0, 0.0
    if since > first_day:
        previous = session.scalar(
            sa.select(DailyLoad)
            .where(DailyLoad.user_id == user_id, DailyLoad.day < since)
            .order_by(DailyLoad.day.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        if previous is not None and previous.day >= first_day:
            start = previous.day + timedelta(days=1)
            initial_ctl, initial_atl = previous.ctl, previous.atl

    thresholds = _Thresholds.load(session, user_id)
    activities = session.scalars(
        sa.select(Activity)
        .where(Activity.user_id == user_id, Activity.start_at >= _start_of(start, tz))
        # El sync escribe con INSERT ... ON CONFLICT: que no se usen copias viejas en memoria.
        .execution_options(populate_existing=True)
    ).all()
    daily: defaultdict[date, float] = defaultdict(float)
    for activity in activities:
        day = _local_day(activity.start_at, tz)
        if not _keeps_current_load(activity, overwrite_existing=overwrite_existing):
            _apply_load(activity, compute_activity_load(activity, thresholds.on(day)))
        if _counts_in_curve(activity, overwrite_existing=overwrite_existing):
            daily[day] += float(activity.load or 0)

    # `start` > `end` si `since` es futuro (p. ej. un umbral que entra en vigor mañana).
    series = (
        fitness_series(
            daily, start=start, end=end, initial_ctl=initial_ctl, initial_atl=initial_atl
        )
        if start <= end
        else []
    )
    session.execute(
        sa.delete(DailyLoad).where(
            DailyLoad.user_id == user_id,
            sa.or_(DailyLoad.day >= start, DailyLoad.day < first_day),
        )
    )
    if series:
        session.execute(sa.insert(DailyLoad), [_row(user_id, day) for day in series])
    session.flush()


# --- Simulación del recálculo histórico ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class LoadChange:
    """Actividad cuya carga o método cambiaría con el recálculo histórico."""

    activity_id: uuid.UUID
    start_at: datetime
    sport: str
    old_load: Decimal | None
    old_method: LoadMethod | None
    new_load: Decimal | None
    new_method: LoadMethod | None

    @property
    def delta(self) -> Decimal | None:
        """Diferencia de carga (nueva − antigua); ``None`` si falta alguna de las dos."""
        if self.old_load is None or self.new_load is None:
            return None
        return self.new_load - self.old_load


def simulate_recompute(
    session: Session, user_id: uuid.UUID, since: date = date.min
) -> list[LoadChange]:
    """Qué actividades desde `since` cambiarían de carga o de método con el recálculo histórico.

    No escribe nada: calcula con los umbrales actuales y compara con lo guardado. Las cargas por
    RPE no se recalculan, así que nunca aparecen. Cambios sólo del IF no se informan.
    """
    tz = ZoneInfo(athlete_timezone(session, user_id))
    thresholds = _Thresholds.load(session, user_id)
    query = (
        sa.select(Activity)
        .where(Activity.user_id == user_id)
        .order_by(Activity.start_at)
        .execution_options(populate_existing=True)
    )
    if since > date.min:
        query = query.where(Activity.start_at >= _start_of(since, tz))
    changes: list[LoadChange] = []
    for activity in session.scalars(query):
        if _keeps_current_load(activity, overwrite_existing=True):
            continue
        day = _local_day(activity.start_at, tz)
        load, method, _ = _stored_values(
            activity, compute_activity_load(activity, thresholds.on(day))
        )
        if (load, method) != (activity.load, activity.load_method):
            changes.append(
                LoadChange(
                    activity.id,
                    activity.start_at,
                    activity.sport,
                    activity.load,
                    activity.load_method,
                    load,
                    method,
                )
            )
    return changes


# --- Simulación de la curva (CTL/ATL/TSB) ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CurveDelta:
    """Diferencia de una curva simulada respecto a la actual en un día."""

    day: date
    ctl: float
    atl: float
    tsb: float


@dataclass(frozen=True, slots=True)
class ExcludedSport:
    sport: str
    activities: int
    load: float


@dataclass(frozen=True, slots=True)
class CurveSimulation:
    """Curva actual frente a dos simulaciones, de la primera actividad a hoy. No escribe nada.

    - `current`: cargas guardadas con la regla de ahora (protección: la carga histórica sigue
      sumando: senderismo, natación, otros y el TSS por FC de la fuerza).
    - `without_historical`: las mismas cargas, sin esa carga histórica. Aísla el efecto de
      excluirla. `excluded` dice cuánta carga y de qué deportes.
    - `after_recompute`: lo que dejaría el recálculo explícito (cargas recalculadas y
      exclusiones).
    """

    current: list[FitnessDay]
    without_historical: list[FitnessDay]
    after_recompute: list[FitnessDay]
    excluded: list[ExcludedSport]

    @staticmethod
    def _deltas(base: list[FitnessDay], other: list[FitnessDay]) -> list[CurveDelta]:
        return [
            CurveDelta(a.day, b.ctl - a.ctl, b.atl - a.atl, b.tsb - a.tsb)
            for a, b in zip(base, other, strict=True)
        ]

    @property
    def exclusion_deltas(self) -> list[CurveDelta]:
        return self._deltas(self.current, self.without_historical)

    @property
    def recompute_deltas(self) -> list[CurveDelta]:
        return self._deltas(self.current, self.after_recompute)


def simulate_curve(
    session: Session, user_id: uuid.UUID, *, today: date | None = None
) -> CurveSimulation:
    """Cuánto cambiaría la curva al excluir la carga histórica (senderismo, natación, otros y el
    TSS por FC de la fuerza), y con el recálculo explícito completo. Calcula desde las
    actividades; no escribe nada."""
    tz = ZoneInfo(athlete_timezone(session, user_id))
    today = today or datetime.now(tz).date()
    activities = session.scalars(
        sa.select(Activity)
        .where(Activity.user_id == user_id)
        .order_by(Activity.start_at)
        .execution_options(populate_existing=True)
    ).all()
    if not activities:
        return CurveSimulation([], [], [], [])
    thresholds = _Thresholds.load(session, user_id)
    current: defaultdict[date, float] = defaultdict(float)
    without: defaultdict[date, float] = defaultdict(float)
    after: defaultdict[date, float] = defaultdict(float)
    excluded: dict[str, list[float]] = defaultdict(list)
    for activity in activities:
        day = _local_day(activity.start_at, tz)
        stored = float(activity.load) if activity.load is not None else 0.0
        if _counts_in_curve(activity, overwrite_existing=False):
            current[day] += stored
        if _counts_in_curve(activity, overwrite_existing=True):
            without[day] += stored
        elif _counts_in_curve(activity, overwrite_existing=False) and _is_historical_load(activity):
            excluded[activity.sport].append(stored)
        if _keeps_current_load(activity, overwrite_existing=True):
            new_load = activity.load
            new_method = activity.load_method
        else:
            new_load, new_method, _ = _stored_values(
                activity, compute_activity_load(activity, thresholds.on(day))
            )
        if (
            activity.duplicate_of_id is None
            and new_load is not None
            and counts_in_daily_load(activity.sport, new_method)
        ):
            after[day] += float(new_load)
    start = _local_day(activities[0].start_at, tz)
    end = max(today, _local_day(activities[-1].start_at, tz))
    return CurveSimulation(
        fitness_series(current, start=start, end=end),
        fitness_series(without, start=start, end=end),
        fitness_series(after, start=start, end=end),
        [ExcludedSport(sport, len(loads), sum(loads)) for sport, loads in sorted(excluded.items())],
    )


def _row(user_id: uuid.UUID, day: FitnessDay) -> dict[str, object]:
    return {
        "user_id": user_id,
        "day": day.day,
        "load": _quantize(day.load, _ONE),
        "ctl": day.ctl,
        "atl": day.atl,
        "tsb": day.tsb,
    }


def recompute_since_activity(
    session: Session, user_id: uuid.UUID, start_at: datetime, *, today: date | None = None
) -> None:
    """Gancho para cuando se crea, modifica o borra una actividad que empezaba en `start_at`."""
    tz = ZoneInfo(athlete_timezone(session, user_id))
    recompute_from(session, user_id, _local_day(start_at, tz), today=today)


def extend_to_today(session: Session, user_id: uuid.UUID) -> None:
    """Completa la serie hasta hoy sin tocar el pasado (p. ej. tras un sync sin cambios)."""
    recompute_from(session, user_id, today_for(session, user_id))


# --- Lectura ---------------------------------------------------------------------------------


def fitness_range(session: Session, user_id: uuid.UUID, start: date, end: date) -> list[FitnessDay]:
    """Serie diaria de `start` a `end` (incluidos), sin huecos.

    Antes de la primera fila guardada todo es 0 (no hay historia). Después de la última, la
    serie continúa con carga 0 (descanso) desde el último estado guardado.
    """
    rows: Sequence[DailyLoad] = session.scalars(
        sa.select(DailyLoad).where(
            DailyLoad.user_id == user_id, DailyLoad.day >= start, DailyLoad.day <= end
        )
    ).all()
    by_day = {row.day: row for row in rows}
    last = session.scalar(
        sa.select(DailyLoad)
        .where(DailyLoad.user_id == user_id, DailyLoad.day <= end)
        .order_by(DailyLoad.day.desc())
        .limit(1)
    )

    result: list[FitnessDay] = []
    day = start
    while day <= end:
        row = by_day.get(day)
        if row is not None:
            result.append(FitnessDay(day, float(row.load), row.ctl, row.atl, row.tsb))
        elif last is None or day < last.day:
            result.append(FitnessDay(day, 0.0, 0.0, 0.0, 0.0))
        else:
            # Tras la última fila: descanso desde el último estado guardado.
            rest = fitness_series(
                {},
                start=last.day + timedelta(days=1),
                end=end,
                initial_ctl=last.ctl,
                initial_atl=last.atl,
            )
            result.extend(rest_day for rest_day in rest if rest_day.day >= day)
            break
        day += timedelta(days=1)
    return result
