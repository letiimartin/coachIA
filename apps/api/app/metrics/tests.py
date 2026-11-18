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

Avisos de calidad (no impiden la propuesta, pero la atleta los ve antes de aceptarla):

- ``data_gaps``: hay huecos largos dentro del bloque.
- ``pauses``: hay tramos de ``PAUSE_MIN_S`` segundos o más a 0 W dentro del bloque.
- ``high_variability``: el índice de variabilidad (NP / potencia media) supera
  ``VARIABILITY_LIMIT``; un test bien hecho es un esfuerzo constante.
- ``no_warmup``: el bloque empieza menos de ``MIN_WARMUP_S`` segundos después del inicio.

Errores (`ThresholdTestError`, con mensaje apto para el cliente): actividad más corta que el
test, sin datos de potencia o con menos de ``MIN_VALID_FRACTION`` de datos válidos en el
mejor bloque.
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


class QualityWarningCode(enum.StrEnum):
    DATA_GAPS = "data_gaps"
    PAUSES = "pauses"
    HIGH_VARIABILITY = "high_variability"
    NO_WARMUP = "no_warmup"


class ThresholdTestError(Exception):
    """El test no se puede analizar. `code` es estable; el mensaje, apto para el cliente."""

    code = "test_not_analyzable"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ActivityTooShortError(ThresholdTestError):
    code = "test_too_short"


class NoPowerDataError(ThresholdTestError):
    code = "no_power_data"


class InsufficientDataError(ThresholdTestError):
    code = "insufficient_data"


@dataclass(frozen=True, slots=True)
class Sample:
    """Un registro de la actividad. `offset_s`: segundos desde el inicio del registro."""

    offset_s: float
    power_w: float | None
    heart_rate_bpm: float | None = None


@dataclass(frozen=True, slots=True)
class QualityWarning:
    code: QualityWarningCode
    message: str


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
    warnings: tuple[QualityWarning, ...]


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


def _longest_zero_run(values: Sequence[float | None]) -> int:
    """Segundos seguidos a 0 W (con dato) más largos."""
    longest = current = 0
    for value in values:
        current = current + 1 if value == 0 else 0
        longest = max(longest, current)
    return longest


def _round_half_up(value: float) -> int:
    return math.floor(value + 0.5)


def analyze_ftp_20min(samples: Sequence[Sample]) -> FtpTestResult:
    """Detecta el mejor bloque de 20 minutos y propone el FTP (95 % de su potencia media)."""
    window = FTP_20MIN_DURATION_S
    if not samples:
        raise ActivityTooShortError("La actividad no tiene registros.")
    grid = _grid(samples)
    if len(grid.power) < window:
        raise ActivityTooShortError("La actividad dura menos que los 20 minutos del test.")
    if all(value is None for value in grid.power):
        raise NoPowerDataError("La actividad no tiene datos de potencia.")

    start = _best_window(grid.power, window)
    block = grid.power[start : start + window]
    valid = sum(value is not None for value in block)
    if valid < window * MIN_VALID_FRACTION:
        raise InsufficientDataError(
            "El mejor bloque de 20 minutos tiene demasiados huecos sin potencia."
        )
    watts = [value or 0.0 for value in block]
    avg_power = sum(watts) / window
    if avg_power <= 0:
        raise NoPowerDataError("La actividad no tiene datos de potencia.")
    np_w = normalized_power(watts)
    variability = np_w / avg_power
    heart_rates = [hr for hr in grid.heart_rate[start : start + window] if hr is not None]
    valid_pct = valid / window * 100

    warnings: list[QualityWarning] = []
    if valid < window:
        warnings.append(
            QualityWarning(
                QualityWarningCode.DATA_GAPS,
                f"Faltan datos de potencia en {window - valid} s del bloque"
                f" ({valid_pct:.1f} % de datos válidos).",
            )
        )
    longest_pause = _longest_zero_run(block)
    if longest_pause >= PAUSE_MIN_S:
        warnings.append(
            QualityWarning(
                QualityWarningCode.PAUSES,
                f"Hay una pausa de {longest_pause} s a 0 W dentro del bloque.",
            )
        )
    if variability > VARIABILITY_LIMIT:
        warnings.append(
            QualityWarning(
                QualityWarningCode.HIGH_VARIABILITY,
                f"Variabilidad alta (NP / media = {variability:.2f}): el test debería ser un"
                " esfuerzo constante.",
            )
        )
    if start < MIN_WARMUP_S:
        warnings.append(
            QualityWarning(
                QualityWarningCode.NO_WARMUP,
                f"El bloque empieza a los {start // 60} min: no hay un calentamiento previo"
                f" de al menos {MIN_WARMUP_S // 60} min.",
            )
        )

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
        warnings=tuple(warnings),
    )
