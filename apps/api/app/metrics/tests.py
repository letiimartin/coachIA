"""Tests de umbral: detección del intervalo del test y cálculo de la propuesta.

Sin estado y sin E/S: recibe la serie por segundo de una actividad (ya leída del FIT) y
devuelve el intervalo detectado, sus métricas y el umbral propuesto. Nunca guarda nada ni
cambia ningún umbral: el resultado es una **propuesta** que la atleta acepta o rechaza.

Protocolo `ftp_20min` (Allen y Coggan, *Training and Racing with a Power Meter*):

- El intervalo del test es el mejor bloque de 20 minutos de potencia media de la actividad
  (media móvil de 1200 s sobre una rejilla de 1 Hz).
- FTP propuesto = 95 % de la potencia media del bloque.
- La FC del bloque (media y máxima) se informa, pero no se propone FC umbral con este test.

Tratamiento de los huecos (segundos sin registro o sin potencia):

- Los huecos cortos (hasta ``MAX_FILLED_GAP_S`` segundos, pérdidas puntuales del sensor) se
  rellenan con el último valor de potencia.
- Los huecos largos **no se interpolan**: cuentan como 0 W en la media (no se inventa
  potencia) y como datos no válidos. Así, un bloque con una pausa larga sale penalizado y
  con aviso.

Criterios de calidad. Cada uno se evalúa con un valor medido y un umbral, y el resultado
(`QualityCheck`) dice si se cumple, si bloquea la propuesta o sólo avisa y un mensaje legible.

Bloquean la propuesta (`ThresholdTestError`, cuyo `code` es el del criterio):

- ``test_too_short``: la actividad dura menos que el test (``FTP_20MIN_DURATION_S``).
- ``no_power_data``: no hay potencia (potencia media del mejor bloque de 0 W).
- ``insufficient_data``: menos de ``MIN_VALID_FRACTION`` de datos válidos en el mejor bloque.

Sólo avisan (la atleta los ve antes de aceptar la propuesta):

- ``data_gaps``: hay huecos de más de ``MAX_FILLED_GAP_S`` segundos dentro del bloque.
- ``pauses``: hay tramos de ``PAUSE_MIN_S`` segundos o más a 0 W dentro del bloque.
- ``high_variability``: el índice de variabilidad (NP / potencia media) supera
  ``VARIABILITY_LIMIT``; un test bien hecho es un esfuerzo constante.
- ``no_warmup``: el bloque empieza menos de ``MIN_WARMUP_S`` segundos después del inicio.
"""

import enum
import math
from collections.abc import Sequence
from dataclasses import dataclass

FTP_20MIN_DURATION_S = 1200
FTP_20MIN_FACTOR = 0.95
MAX_FILLED_GAP_S = 3
PAUSE_MIN_S = 10
VARIABILITY_LIMIT = 1.05
MIN_WARMUP_S = 600
MIN_VALID_FRACTION = 0.5
# Ventana de la potencia normalizada (Coggan).
NP_WINDOW_S = 30


class ThresholdProtocol(enum.StrEnum):
    FTP_20MIN = "ftp_20min"


class QualityCriterion(enum.StrEnum):
    """Criterios de calidad del test. Los tres primeros bloquean la propuesta."""

    TEST_TOO_SHORT = "test_too_short"
    NO_POWER_DATA = "no_power_data"
    INSUFFICIENT_DATA = "insufficient_data"
    DATA_GAPS = "data_gaps"
    PAUSES = "pauses"
    HIGH_VARIABILITY = "high_variability"
    NO_WARMUP = "no_warmup"


class Comparison(enum.StrEnum):
    """Condición que cumple el valor medido frente al umbral cuando el criterio se cumple."""

    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"


@dataclass(frozen=True, slots=True)
class QualityCheck:
    """Evaluación de un criterio: se cumple si `measured <comparison> threshold`.

    `unit`: `s`, `W`, `%` o vacío (adimensional, como el índice de variabilidad).
    """

    criterion: QualityCriterion
    measured: float
    threshold: float
    comparison: Comparison
    unit: str
    blocking: bool
    message: str

    @property
    def passed(self) -> bool:
        measured, limit = self.measured, self.threshold
        match self.comparison:
            case Comparison.GT:
                return measured > limit
            case Comparison.GE:
                return measured >= limit
            case Comparison.LT:
                return measured < limit
            case Comparison.LE:
                return measured <= limit


class ThresholdTestError(Exception):
    """El test no se puede analizar: `check` es el criterio bloqueante que no se cumple."""

    def __init__(self, check: QualityCheck):
        super().__init__(check.message)
        self.check = check
        self.code = check.criterion.value
        self.message = check.message


class ActivityTooShortError(ThresholdTestError):
    pass


class NoPowerDataError(ThresholdTestError):
    pass


class InsufficientDataError(ThresholdTestError):
    pass


@dataclass(frozen=True, slots=True)
class Sample:
    """Un registro de la actividad. `offset_s`: segundos desde el inicio del registro."""

    offset_s: float
    power_w: float | None
    heart_rate_bpm: float | None = None


@dataclass(frozen=True, slots=True)
class FtpTestResult:
    """Intervalo detectado (offsets en segundos desde el primer registro) y propuesta."""

    protocol: ThresholdProtocol
    start_offset_s: int
    end_offset_s: int
    avg_power_w: float
    normalized_power_w: float
    variability_index: float
    avg_hr_bpm: float | None
    max_hr_bpm: float | None
    valid_data_pct: float
    warmup_s: int
    proposed_ftp_w: int
    # Todos los criterios evaluados, en orden; `warnings`, los que avisan y no se cumplen.
    checks: tuple[QualityCheck, ...]

    @property
    def warnings(self) -> tuple[QualityCheck, ...]:
        return tuple(check for check in self.checks if not check.passed)


@dataclass(frozen=True, slots=True)
class _Grid:
    """Serie a 1 Hz desde el primer registro. `power` ya tiene los huecos cortos rellenos."""

    first_offset_s: int
    power: list[float | None]
    heart_rate: list[float | None]


def _check_value(value: float | None) -> float | None:
    if value is None:
        return None
    if not math.isfinite(value) or value < 0:
        raise ValueError("los datos deben ser números no negativos")
    return value


def _grid(samples: Sequence[Sample]) -> _Grid:
    ordered = sorted(samples, key=lambda sample: sample.offset_s)
    first = round(ordered[0].offset_s)
    length = round(ordered[-1].offset_s) - first + 1
    power: list[float | None] = [None] * length
    heart_rate: list[float | None] = [None] * length
    for sample in ordered:
        if not math.isfinite(sample.offset_s):
            raise ValueError("offset_s debe ser finito")
        index = round(sample.offset_s) - first
        power[index] = _check_value(sample.power_w)
        heart_rate[index] = _check_value(sample.heart_rate_bpm)
    _fill_short_gaps(power)
    return _Grid(first_offset_s=first, power=power, heart_rate=heart_rate)


def _fill_short_gaps(values: list[float | None]) -> None:
    """Rellena con el valor anterior los huecos de hasta MAX_FILLED_GAP_S entre dos datos."""
    index = 0
    while index < len(values):
        if values[index] is not None:
            index += 1
            continue
        end = index
        while end < len(values) and values[end] is None:
            end += 1
        inside = index > 0 and end < len(values)
        if inside and end - index <= MAX_FILLED_GAP_S:
            for gap in range(index, end):
                values[gap] = values[index - 1]
        index = end


def _best_window(power: list[float | None], window: int) -> int:
    """Inicio del bloque de `window` segundos con mayor potencia media (el primero si empata)."""
    running = sum(value or 0.0 for value in power[:window])
    best_sum, best_start = running, 0
    for start in range(1, len(power) - window + 1):
        running += (power[start + window - 1] or 0.0) - (power[start - 1] or 0.0)
        # Margen para que los errores de redondeo de la suma acumulada no cambien el empate.
        if running > best_sum + 1e-6:
            best_sum, best_start = running, start
    return best_start


def normalized_power(power: Sequence[float]) -> float:
    """Potencia normalizada de Coggan: media móvil de 30 s, a la 4ª, media y raíz 4ª."""
    if len(power) < NP_WINDOW_S:
        return sum(power) / len(power) if power else 0.0
    running = sum(power[:NP_WINDOW_S])
    fourth_powers = [(running / NP_WINDOW_S) ** 4]
    for index in range(NP_WINDOW_S, len(power)):
        running += power[index] - power[index - NP_WINDOW_S]
        fourth_powers.append((running / NP_WINDOW_S) ** 4)
    return float((sum(fourth_powers) / len(fourth_powers)) ** 0.25)


def _longest_run(values: Sequence[float | None], target: float | None) -> int:
    """Segundos seguidos más largos con el valor `target` (0 para pausas, None para huecos)."""
    longest = current = 0
    for value in values:
        current = current + 1 if value == target else 0
        longest = max(longest, current)
    return longest


def _round_half_up(value: float) -> int:
    return math.floor(value + 0.5)


def _minutes(seconds: float) -> str:
    return f"{seconds / 60:.1f}".rstrip("0").rstrip(".")


def _duration_check(duration_s: int) -> QualityCheck:
    limit = FTP_20MIN_DURATION_S
    if duration_s >= limit:
        message = f"La actividad dura {_minutes(duration_s)} min (mínimo {_minutes(limit)} min)."
    elif duration_s == 0:
        message = "La actividad no tiene registros."
    else:
        message = (
            f"La actividad dura {_minutes(duration_s)} min: menos que los"
            f" {_minutes(limit)} min del test."
        )
    return QualityCheck(
        QualityCriterion.TEST_TOO_SHORT, duration_s, limit, Comparison.GE, "s", True, message
    )


def _power_check(avg_power_w: float) -> QualityCheck:
    message = (
        f"Potencia media del bloque: {avg_power_w:.0f} W."
        if avg_power_w > 0
        else "La actividad no tiene datos de potencia."
    )
    return QualityCheck(
        QualityCriterion.NO_POWER_DATA,
        round(avg_power_w, 1),
        0,
        Comparison.GT,
        "W",
        True,
        message,
    )


def _valid_data_check(valid_pct: float) -> QualityCheck:
    limit = MIN_VALID_FRACTION * 100
    measured = round(valid_pct, 1)
    message = (
        f"{measured:.1f} % del bloque tiene datos de potencia (mínimo {limit:.0f} %)."
        if measured >= limit
        else f"Sólo {measured:.1f} % del mejor bloque de 20 minutos tiene datos de potencia"
        f" (mínimo {limit:.0f} %): hay demasiados huecos."
    )
    return QualityCheck(
        QualityCriterion.INSUFFICIENT_DATA, measured, limit, Comparison.GE, "%", True, message
    )


def _gaps_check(longest_gap_s: int, missing_s: int, valid_pct: float) -> QualityCheck:
    limit = MAX_FILLED_GAP_S
    message = (
        f"Sin huecos de más de {limit} s en el bloque."
        if longest_gap_s <= limit
        else f"Hay huecos sin potencia de hasta {longest_gap_s} s en el bloque (se toleran"
        f" {limit} s); faltan datos en {missing_s} s ({valid_pct:.1f} % de datos válidos)."
    )
    return QualityCheck(
        QualityCriterion.DATA_GAPS, longest_gap_s, limit, Comparison.LE, "s", False, message
    )


def _pauses_check(longest_pause_s: int) -> QualityCheck:
    limit = PAUSE_MIN_S
    message = (
        f"Sin pausas de {limit} s o más a 0 W en el bloque."
        if longest_pause_s < limit
        else f"Hay una pausa de {longest_pause_s} s a 0 W dentro del bloque (avisa a partir"
        f" de {limit} s)."
    )
    return QualityCheck(
        QualityCriterion.PAUSES, longest_pause_s, limit, Comparison.LT, "s", False, message
    )


def _variability_check(variability: float) -> QualityCheck:
    limit = VARIABILITY_LIMIT
    measured = round(variability, 3)
    # El criterio se evalúa sobre el valor redondeado que se muestra, para que sean coherentes.
    message = (
        f"Esfuerzo constante (NP / media = {measured:.3f}; máximo {limit:.2f})."
        if measured <= limit
        else f"Variabilidad alta (NP / media = {measured:.3f}; máximo {limit:.2f}): el test"
        " debería ser un esfuerzo constante."
    )
    return QualityCheck(
        QualityCriterion.HIGH_VARIABILITY, measured, limit, Comparison.LE, "", False, message
    )


def _warmup_check(warmup_s: int) -> QualityCheck:
    limit = MIN_WARMUP_S
    message = (
        f"Calentamiento de {_minutes(warmup_s)} min antes del bloque (mínimo"
        f" {_minutes(limit)} min)."
        if warmup_s >= limit
        else f"El bloque empieza a los {_minutes(warmup_s)} min: no hay un calentamiento previo"
        f" de al menos {_minutes(limit)} min."
    )
    return QualityCheck(
        QualityCriterion.NO_WARMUP, warmup_s, limit, Comparison.GE, "s", False, message
    )


def _require(check: QualityCheck, error: type[ThresholdTestError]) -> QualityCheck:
    if not check.passed:
        raise error(check)
    return check


def analyze_ftp_20min(samples: Sequence[Sample]) -> FtpTestResult:
    """Detecta el mejor bloque de 20 minutos y propone el FTP (95 % de su potencia media).

    Lanza `ThresholdTestError` (con el criterio que falla) si un criterio bloqueante no se
    cumple; los demás criterios quedan en `checks` y, si no se cumplen, en `warnings`.
    """
    window = FTP_20MIN_DURATION_S
    if not samples:
        raise ActivityTooShortError(_duration_check(0))
    grid = _grid(samples)
    checks = [_require(_duration_check(len(grid.power)), ActivityTooShortError)]
    if all(value is None for value in grid.power):
        raise NoPowerDataError(_power_check(0.0))

    start = _best_window(grid.power, window)
    block = grid.power[start : start + window]
    valid = sum(value is not None for value in block)
    valid_pct = valid / window * 100
    valid_check = _require(_valid_data_check(valid_pct), InsufficientDataError)
    watts = [value or 0.0 for value in block]
    avg_power = sum(watts) / window
    checks.append(_require(_power_check(avg_power), NoPowerDataError))
    checks.append(valid_check)
    np_w = normalized_power(watts)
    variability = np_w / avg_power
    heart_rates = [hr for hr in grid.heart_rate[start : start + window] if hr is not None]

    checks += [
        _gaps_check(_longest_run(block, None), window - valid, valid_pct),
        _pauses_check(_longest_run(block, 0)),
        _variability_check(variability),
        _warmup_check(start),
    ]

    return FtpTestResult(
        protocol=ThresholdProtocol.FTP_20MIN,
        start_offset_s=grid.first_offset_s + start,
        end_offset_s=grid.first_offset_s + start + window,
        avg_power_w=avg_power,
        normalized_power_w=np_w,
        variability_index=variability,
        avg_hr_bpm=sum(heart_rates) / len(heart_rates) if heart_rates else None,
        max_hr_bpm=max(heart_rates) if heart_rates else None,
        valid_data_pct=valid_pct,
        warmup_s=start,
        proposed_ftp_w=_round_half_up(avg_power * FTP_20MIN_FACTOR),
        checks=tuple(checks),
    )
