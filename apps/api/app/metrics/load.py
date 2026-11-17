"""Carga de entrenamiento (TSS y equivalentes) de una actividad.

Todas las variantes siguen la definición de Coggan del Training Stress Score:

    TSS = (s · NP · IF) / (FTP · 3600) · 100 = horas · IF² · 100

donde ``IF`` (factor de intensidad) es la intensidad relativa al umbral. Una hora exactamente
al umbral vale 100. Lo que cambia entre métodos es cómo se obtiene ``IF``:

- Potencia (``POWER``): ``IF = NP / FTP``. Fórmula original (Allen y Coggan, *Training and
  Racing with a Power Meter*).
- Frecuencia cardiaca (``HEART_RATE``, hrTSS): ``IF = FC media / LTHR``. **Aproximación**:
  el hrTSS de TrainingPeaks se calcula con el tiempo en cada zona de FC, que necesita el
  stream de FC. Con la media sólo, la FC subestima los esfuerzos variables (series).
- Ritmo (``PACE``, rTSS): ``IF = ritmo umbral / ritmo medio`` (en s/km, un ritmo más rápido es
  un número menor). **Aproximación**: el rTSS de TrainingPeaks usa el ritmo ajustado por
  pendiente (NGP), que necesita los streams del FIT; con el ritmo medio, el desnivel
  (trail) queda infravalorado.

El factor de intensidad (IF) que se publica va por método: de momento sólo se publica con
potencia (``NP / FTP``, el IF de Coggan). Con FC y ritmo el cociente se usa en la fórmula pero
el IF devuelto es ``None``, porque es una aproximación que no equivale al IF de potencia. Para
publicarlo con otro método basta con añadirlo a ``INTENSITY_FACTOR_METHODS`` (o darle su propio
cálculo en ``intensity_factor_for``) sin tocar el resto.

Las funciones devuelven ``None`` cuando falta el dato o el umbral (o no es positivo): no se
inventa carga. Una duración de 0 da carga 0. Valores negativos o no finitos son un error.
"""

import math
from collections.abc import Callable, Mapping
from typing import NamedTuple, TypeGuard

from app.models.activity import LoadMethod

SECONDS_PER_HOUR = 3600.0


class LoadResult(NamedTuple):
    """Resultado del contrato con el sync: ``(load, method, intensity_factor)``.

    ``intensity_factor`` es ``None`` si el método no publica IF (ver ``intensity_factor_for``).
    """

    load: float
    method: LoadMethod
    intensity_factor: float | None


# Cálculo del IF publicado por método. Recibe el cociente de intensidad usado en el TSS.
# Un método sin entrada aquí no publica IF.
INTENSITY_FACTOR_METHODS: Mapping[LoadMethod, Callable[[float], float]] = {
    LoadMethod.POWER: lambda ratio: ratio,
}


def intensity_factor_for(method: LoadMethod, ratio: float) -> float | None:
    """IF publicado para ``method`` a partir del cociente de intensidad; ``None`` si no hay."""
    compute = INTENSITY_FACTOR_METHODS.get(method)
    return compute(ratio) if compute is not None else None


def _check_duration(duration_s: float) -> None:
    if not math.isfinite(duration_s) or duration_s < 0:
        raise ValueError("duration_s debe ser un número no negativo")


def _usable(value: float | None) -> TypeGuard[float]:
    """Un dato o umbral sólo sirve si existe y es positivo. Negativos o no finitos: error."""
    if value is None:
        return False
    if not math.isfinite(value) or value < 0:
        raise ValueError("los datos y umbrales deben ser números no negativos")
    return value > 0


def _tss(duration_s: float, ratio: float, method: LoadMethod) -> LoadResult:
    load = duration_s / SECONDS_PER_HOUR * ratio**2 * 100.0
    return LoadResult(load, method, intensity_factor_for(method, ratio))


def power_tss(duration_s: float, np_w: float | None, ftp_w: float | None) -> LoadResult | None:
    """TSS por potencia: ``horas · (NP/FTP)² · 100``."""
    _check_duration(duration_s)
    if _usable(np_w) and _usable(ftp_w):
        return _tss(duration_s, np_w / ftp_w, LoadMethod.POWER)
    return None


def hr_tss(
    duration_s: float, avg_hr_bpm: float | None, lthr_bpm: float | None
) -> LoadResult | None:
    """hrTSS aproximado: ``horas · (FC media / LTHR)² · 100``."""
    _check_duration(duration_s)
    if _usable(avg_hr_bpm) and _usable(lthr_bpm):
        return _tss(duration_s, avg_hr_bpm / lthr_bpm, LoadMethod.HEART_RATE)
    return None


def run_tss(
    duration_s: float,
    avg_pace_s_per_km: float | None,
    threshold_pace_s_per_km: float | None,
) -> LoadResult | None:
    """rTSS aproximado: ``horas · (ritmo umbral / ritmo medio)² · 100`` (ritmos en s/km)."""
    _check_duration(duration_s)
    if _usable(avg_pace_s_per_km) and _usable(threshold_pace_s_per_km):
        return _tss(duration_s, threshold_pace_s_per_km / avg_pace_s_per_km, LoadMethod.PACE)
    return None


def pace_s_per_km(speed_mps: float | None) -> float | None:
    """Convierte velocidad (m/s, como ``activities.avg_speed_mps``) en ritmo (s/km)."""
    if _usable(speed_mps):
        return 1000.0 / speed_mps
    return None


def activity_load(
    duration_s: float,
    *,
    normalized_power_w: float | None = None,
    ftp_w: float | None = None,
    avg_hr_bpm: float | None = None,
    lthr_bpm: float | None = None,
    avg_speed_mps: float | None = None,
    threshold_pace_s_per_km: float | None = None,
) -> LoadResult | None:
    """Carga con el mejor método disponible: potencia > FC > ritmo.

    Un método está disponible si tiene a la vez el dato de la actividad y el umbral. Devuelve
    ``None`` si ninguno lo está. La duración la elige quien llama (normalmente ``moving_s``).
    """
    return (
        power_tss(duration_s, normalized_power_w, ftp_w)
        or hr_tss(duration_s, avg_hr_bpm, lthr_bpm)
        or run_tss(duration_s, pace_s_per_km(avg_speed_mps), threshold_pace_s_per_km)
    )
