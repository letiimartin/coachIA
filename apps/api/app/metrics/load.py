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

El método se elige por deporte con una sola tabla, ``LOAD_RULES``: cada deporte tiene sus
métodos en orden de preferencia y dice si su carga suma en la carga diaria (CTL/ATL/TSB).
Un deporte sin métodos sólo se registra: no se le calcula carga ni suma en la curva.

- Ciclismo: potencia → FC sobre el LTHR de ciclismo → RPE.
- Carrera: ritmo → FC sobre el LTHR de carrera (p. ej. en cinta sin sensor) → RPE.
- Trail: FC sobre el LTHR de carrera → RPE. El ritmo **nunca** se usa en trail: el desnivel
  lo invalida.
- Fuerza (``strength``): sólo ``session_rpe`` = minutos × RPE de la sesión (Foster), nunca
  potencia, ritmo ni FC. No es TSS y no suma en la carga diaria.
- Senderismo, natación y otros: sólo se registran. No se calcula su carga (ni con la FC
  umbral de carrera) ni suman en CTL/ATL. Las cargas que ya tengan guardadas se conservan como
  dato histórico (ver ``app.services.fitness``).

Qué LTHR usa cada deporte lo decide ``app.metrics.zones.lthr_field_for``.

El paso RPE de resistencia (estimación de TSS a partir del RPE) no tiene todavía una fórmula
aprobada: devuelve ``None``. Las cargas por RPE ya guardadas (manuales) las conserva quien
llama. Sin datos suficientes la carga es ``None``. ``LoadResult.method`` dice siempre qué se
usó.

Las funciones devuelven ``None`` cuando falta el dato o el umbral (o no es positivo): no se
inventa carga. Una duración de 0 da carga 0. Valores negativos o no finitos son un error.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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


def session_rpe_load(duration_s: float | None, rpe: int | None) -> LoadResult | None:
    """Carga de una sesión de fuerza: ``minutos × RPE`` (1-10). ``None`` sin RPE o sin tiempo."""
    if rpe is None or duration_s is None:
        return None
    _check_duration(duration_s)
    if not 1 <= rpe <= 10:
        raise ValueError("el RPE debe estar entre 1 y 10")
    return LoadResult(duration_s / 60.0 * rpe, LoadMethod.SESSION_RPE, None)


@dataclass(frozen=True, slots=True)
class LoadInputs:
    """Datos de la actividad y umbrales que corresponden a su deporte."""

    moving_s: float | None
    elapsed_s: float | None = None
    normalized_power_w: float | None = None
    ftp_w: float | None = None
    avg_hr_bpm: float | None = None
    lthr_bpm: float | None = None
    avg_speed_mps: float | None = None
    threshold_pace_s_per_km: float | None = None
    rpe: int | None = None


def _with_moving(
    compute: Callable[[float, LoadInputs], LoadResult | None],
) -> Callable[[LoadInputs], LoadResult | None]:
    """Los métodos TSS usan el tiempo en movimiento; sin él no hay carga."""

    def run(inputs: LoadInputs) -> LoadResult | None:
        return None if inputs.moving_s is None else compute(inputs.moving_s, inputs)

    return run


# Cálculo de cada método. Uno que devuelve None no está disponible y se pasa al siguiente.
_METHODS: Mapping[LoadMethod, Callable[[LoadInputs], LoadResult | None]] = {
    LoadMethod.POWER: _with_moving(lambda s, i: power_tss(s, i.normalized_power_w, i.ftp_w)),
    LoadMethod.HEART_RATE: _with_moving(lambda s, i: hr_tss(s, i.avg_hr_bpm, i.lthr_bpm)),
    LoadMethod.PACE: _with_moving(
        lambda s, i: run_tss(s, pace_s_per_km(i.avg_speed_mps), i.threshold_pace_s_per_km)
    ),
    # RPE → TSS de resistencia: sin fórmula aprobada (#22), nunca se inventa.
    LoadMethod.RPE: lambda inputs: None,
    # Fuerza: tiempo en movimiento o, si no hay, el total.
    LoadMethod.SESSION_RPE: lambda i: session_rpe_load(
        i.moving_s if i.moving_s is not None else i.elapsed_s, i.rpe
    ),
}


@dataclass(frozen=True, slots=True)
class SportLoadRule:
    """Métodos de carga de un deporte, en orden de preferencia, y si suma en CTL/ATL."""

    methods: tuple[LoadMethod, ...]
    endurance: bool

    @property
    def registered_only(self) -> bool:
        """Sin métodos: la actividad se registra, pero no se le calcula carga."""
        return not self.methods


_REGISTERED_ONLY = SportLoadRule((), endurance=False)

# Única correspondencia deporte → métodos. Una disciplina nueva sólo añade una entrada.
LOAD_RULES: Mapping[Sport, SportLoadRule] = {
    Sport.CYCLING: SportLoadRule(
        (LoadMethod.POWER, LoadMethod.HEART_RATE, LoadMethod.RPE), endurance=True
    ),
    Sport.RUNNING: SportLoadRule(
        (LoadMethod.PACE, LoadMethod.HEART_RATE, LoadMethod.RPE), endurance=True
    ),
    Sport.TRAIL_RUNNING: SportLoadRule((LoadMethod.HEART_RATE, LoadMethod.RPE), endurance=True),
    Sport.STRENGTH: SportLoadRule((LoadMethod.SESSION_RPE,), endurance=False),
    Sport.HIKING: _REGISTERED_ONLY,
    Sport.SWIMMING: _REGISTERED_ONLY,
    Sport.OTHER: _REGISTERED_ONLY,
}


def counts_in_daily_load(sport: Sport, method: LoadMethod | None) -> bool:
    """La carga diaria (CTL/ATL/TSB) sólo suma resistencia, y nunca ``session_rpe``."""
    return LOAD_RULES[sport].endurance and method is not LoadMethod.SESSION_RPE


def activity_load(
    sport: Sport,
    moving_s: float | None,
    *,
    elapsed_s: float | None = None,
    normalized_power_w: float | None = None,
    ftp_w: float | None = None,
    avg_hr_bpm: float | None = None,
    lthr_bpm: float | None = None,
    avg_speed_mps: float | None = None,
    threshold_pace_s_per_km: float | None = None,
    rpe: int | None = None,
) -> LoadResult | None:
    """Carga con el primer método disponible de ``LOAD_RULES[sport]`` (ver el módulo).

    ``lthr_bpm`` es el LTHR que corresponde al deporte (``lthr_field_for``) y ``rpe`` el RPE de
    la sesión (1-10). Un método está disponible si tiene a la vez el dato de la actividad y el
    umbral. Devuelve ``None`` si ninguno lo está.
    """
    if moving_s is not None:
        _check_duration(moving_s)
    inputs = LoadInputs(
        moving_s,
        elapsed_s,
        normalized_power_w,
        ftp_w,
        avg_hr_bpm,
        lthr_bpm,
        avg_speed_mps,
        threshold_pace_s_per_km,
        rpe,
    )
    for method in LOAD_RULES[sport].methods:
        result = _METHODS[method](inputs)
        if result is not None:
            return result
    return None
