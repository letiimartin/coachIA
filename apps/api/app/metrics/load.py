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

El método se elige por disciplina (``activity_load``), no con un orden único para todas:

- Ciclismo: potencia → FC sobre el LTHR de ciclismo → RPE.
- Carrera: ritmo → FC sobre el LTHR de carrera (p. ej. en cinta sin sensor) → RPE.
- Trail: FC sobre el LTHR de carrera → RPE. El ritmo **nunca** se usa en trail: el desnivel
  lo invalida.
- Resto de deportes (senderismo, fuerza, natación, otros): FC, como antes (ni potencia ni
  ritmo ni RPE). Qué LTHR usa cada deporte lo decide ``app.metrics.zones.lthr_field_for``.

RPE: mientras no haya una fuente de RPE por actividad ni una fórmula RPE → TSS aprobada, sólo
se conservan las cargas por RPE que ya existen (introducidas a mano); nunca se inventa una.
Sin datos suficientes la carga es ``None``. ``LoadResult.method`` dice siempre qué se usó.

Las funciones devuelven ``None`` cuando falta el dato o el umbral (o no es positivo): no se
inventa carga. Una duración de 0 da carga 0. Valores negativos o no finitos son un error.
"""

import math
from collections.abc import Callable, Mapping
from typing import NamedTuple, TypeGuard

from app.models.activity import LoadMethod
from app.models.common import Sport

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


def rpe_load(load: float | None) -> LoadResult | None:
    """Carga por RPE ya registrada (manual): se conserva tal cual, sin IF."""
    if load is None:
        return None
    if not math.isfinite(load) or load < 0:
        raise ValueError("los datos y umbrales deben ser números no negativos")
    return LoadResult(load, LoadMethod.RPE, None)


def activity_load(
    sport: Sport,
    duration_s: float,
    *,
    normalized_power_w: float | None = None,
    ftp_w: float | None = None,
    avg_hr_bpm: float | None = None,
    lthr_bpm: float | None = None,
    avg_speed_mps: float | None = None,
    threshold_pace_s_per_km: float | None = None,
    rpe: float | None = None,
) -> LoadResult | None:
    """Carga de una actividad con el método de su disciplina (ver el docstring del módulo).

    ``lthr_bpm`` es el LTHR que corresponde al deporte (``lthr_field_for``) y ``rpe`` una carga
    por RPE ya registrada. Un método está disponible si tiene a la vez el dato de la actividad y
    el umbral. Devuelve ``None`` si el de la disciplina no lo está. La duración la elige quien
    llama (normalmente ``moving_s``).
    """
    _check_duration(duration_s)
    if sport is Sport.CYCLING:
        return (
            power_tss(duration_s, normalized_power_w, ftp_w)
            or hr_tss(duration_s, avg_hr_bpm, lthr_bpm)
            or rpe_load(rpe)
        )
    if sport is Sport.RUNNING:
        return (
            run_tss(duration_s, pace_s_per_km(avg_speed_mps), threshold_pace_s_per_km)
            or hr_tss(duration_s, avg_hr_bpm, lthr_bpm)
            or rpe_load(rpe)
        )
    if sport is Sport.TRAIL_RUNNING:
        return hr_tss(duration_s, avg_hr_bpm, lthr_bpm) or rpe_load(rpe)
    return hr_tss(duration_s, avg_hr_bpm, lthr_bpm)
