"""Forma física (CTL), fatiga (ATL) y frescura (TSB): el Performance Management Chart.

Modelo de Banister simplificado tal como lo usa TrainingPeaks (Coggan): medias móviles
exponenciales de la carga diaria.

    CTL_hoy = CTL_ayer + (carga_hoy − CTL_ayer) / 42
    ATL_hoy = ATL_ayer + (carga_hoy − ATL_ayer) / 7
    TSB_hoy = CTL_hoy − ATL_hoy

Se usa ``TSB = CTL − ATL`` del mismo día, después de sumar la carga de ese día (como
intervals.icu). TrainingPeaks muestra la forma de hoy con los valores de ayer; se obtiene
leyendo el TSB del día anterior.

La serie es diaria y continua: los días sin actividad cuentan con carga 0, que es lo que hace
caer CTL y ATL en el descanso.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta

CTL_TIME_CONSTANT_DAYS = 42
ATL_TIME_CONSTANT_DAYS = 7


@dataclass(frozen=True, slots=True)
class FitnessDay:
    day: date
    load: float
    ctl: float
    atl: float
    tsb: float


def fill_daily_load(
    daily_load: Mapping[date, float], start: date, end: date
) -> list[tuple[date, float]]:
    """Serie continua de ``start`` a ``end`` (ambos incluidos), con 0 en los días sin carga."""
    if start > end:
        raise ValueError("start no puede ser posterior a end")
    days = (end - start).days + 1
    series: list[tuple[date, float]] = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        load = float(daily_load.get(day, 0.0))
        if not math.isfinite(load) or load < 0:
            raise ValueError(f"la carga del {day.isoformat()} debe ser un número no negativo")
        series.append((day, load))
    return series


def fitness_series(
    daily_load: Mapping[date, float],
    *,
    start: date | None = None,
    end: date | None = None,
    initial_ctl: float = 0.0,
    initial_atl: float = 0.0,
    ctl_days: int = CTL_TIME_CONSTANT_DAYS,
    atl_days: int = ATL_TIME_CONSTANT_DAYS,
) -> list[FitnessDay]:
    """CTL, ATL y TSB de cada día entre ``start`` y ``end``.

    ``daily_load`` es la carga total de cada día (la suma de sus actividades). Por defecto el
    rango va del primer al último día con carga; los días de ``daily_load`` fuera del rango se
    ignoran, y la historia anterior se resume en ``initial_ctl`` e ``initial_atl`` (el estado
    al final del día anterior a ``start``). Sin datos ni rango devuelve una lista vacía.
    """
    if ctl_days <= 0 or atl_days <= 0:
        raise ValueError("las constantes de tiempo deben ser positivas")
    if start is None or end is None:
        if not daily_load:
            return []
        start = start if start is not None else min(daily_load)
        end = end if end is not None else max(daily_load)

    ctl, atl = initial_ctl, initial_atl
    result: list[FitnessDay] = []
    for day, load in fill_daily_load(daily_load, start, end):
        ctl += (load - ctl) / ctl_days
        atl += (load - atl) / atl_days
        result.append(FitnessDay(day, load, ctl, atl, ctl - atl))
    return result
