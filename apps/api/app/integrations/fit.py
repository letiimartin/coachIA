"""Lectura de ficheros FIT (registros por segundo) con `fitdecode`.

Sólo extrae lo que necesita el motor de métricas: de cada mensaje `record`, el instante y la
potencia, la FC y la cadencia. No guarda el fichero ni interpreta nada más (vueltas, eventos o
sesiones). Es independiente del proveedor: sirve para Wahoo y, más adelante, para Suunto.

Errores (`FitError` y subclases), con un mensaje apto para el cliente:
- `FitCorruptError`: el fichero no es un FIT válido (cabecera, CRC o fin inesperado).
- `FitNoRecordsError`: no hay registros con instante.
"""

import io
from dataclasses import dataclass
from datetime import UTC, datetime

import fitdecode

# Un FIT de una actividad de varias horas a 1 Hz ocupa unos pocos MB.
MAX_FIT_BYTES = 25 * 1024 * 1024


class FitError(Exception):
    """El FIT no se puede usar. El mensaje puede devolverse al cliente."""


class FitCorruptError(FitError):
    pass


class FitNoRecordsError(FitError):
    pass


@dataclass(frozen=True, slots=True)
class FitSample:
    """Un registro del FIT. `None` si el dato falta o el sensor no lo envió."""

    timestamp: datetime
    power_w: float | None
    heart_rate_bpm: float | None
    cadence_rpm: float | None


def _number(frame: fitdecode.FitDataMessage, name: str) -> float | None:
    if not frame.has_field(name):
        return None
    value = frame.get_value(name, fallback=None)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _timestamp(frame: fitdecode.FitDataMessage) -> datetime | None:
    if not frame.has_field("timestamp"):
        return None
    value = frame.get_value("timestamp", fallback=None)
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def parse_records(data: bytes) -> list[FitSample]:
    """Registros del FIT ordenados por instante (si un instante se repite, gana el último)."""
    if len(data) > MAX_FIT_BYTES:
        raise FitCorruptError("El fichero FIT es demasiado grande.")
    by_time: dict[datetime, FitSample] = {}
    try:
        with fitdecode.FitReader(
            io.BytesIO(data),
            check_crc=fitdecode.CrcCheck.RAISE,
            error_handling=fitdecode.ErrorHandling.RAISE,
        ) as reader:
            for frame in reader:
                if not isinstance(frame, fitdecode.FitDataMessage) or frame.name != "record":
                    continue
                timestamp = _timestamp(frame)
                if timestamp is None:
                    continue
                by_time[timestamp] = FitSample(
                    timestamp=timestamp,
                    power_w=_number(frame, "power"),
                    heart_rate_bpm=_number(frame, "heart_rate"),
                    cadence_rpm=_number(frame, "cadence"),
                )
    except (fitdecode.FitError, EOFError, ValueError, KeyError, TypeError) as exc:
        raise FitCorruptError("El fichero FIT está dañado o no es un FIT válido.") from exc
    if not by_time:
        raise FitNoRecordsError("El fichero FIT no tiene registros por segundo.")
    return [by_time[moment] for moment in sorted(by_time)]
