"""Zonas de entrenamiento calculadas a partir de umbrales (nunca se guardan).

- Potencia: 7 zonas de Andrew Coggan sobre el FTP (Allen y Coggan, *Training and Racing with
  a Power Meter*). Los rangos publicados son Z1 ≤55 %, Z2 56-75 %, Z3 76-90 %, Z4 91-105 %,
  Z5 106-120 %, Z6 121-150 % y Z7 >150 %. Aquí se expresan como intervalos contiguos
  ``[inferior, superior)`` usando el límite superior publicado de cada zona como frontera.
- Frecuencia cardiaca: zonas de Joe Friel sobre el LTHR (*The Cyclist's Training Bible* y
  *The Triathlete's Training Bible*), con tablas distintas para ciclismo y carrera.
"""

import enum
import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Zone:
    """Zona ``[low, high)`` en las unidades del umbral (W o ppm). ``high`` None: sin límite."""

    number: int
    code: str
    name: str
    low: float
    high: float | None

    def contains(self, value: float) -> bool:
        return value >= self.low and (self.high is None or value < self.high)


class HrZoneSport(enum.StrEnum):
    """Tabla de Friel a usar: los porcentajes del LTHR difieren entre ciclismo y carrera."""

    CYCLING = "cycling"
    RUNNING = "running"


# (código, nombre, fracción inferior del umbral). La superior es la inferior de la siguiente.
_COGGAN_POWER: tuple[tuple[str, str, float], ...] = (
    ("Z1", "Recuperación activa", 0.0),
    ("Z2", "Resistencia", 0.55),
    ("Z3", "Tempo", 0.75),
    ("Z4", "Umbral", 0.90),
    ("Z5", "VO2máx", 1.05),
    ("Z6", "Capacidad anaeróbica", 1.20),
    ("Z7", "Neuromuscular", 1.50),
)

# Friel, ciclismo: Z1 <81 %, Z2 81-89 %, Z3 90-93 %, Z4 94-99 %, Z5a 100-102 %,
# Z5b 103-106 %, Z5c >106 % del LTHR.
_FRIEL_HR_CYCLING: tuple[tuple[str, str, float], ...] = (
    ("Z1", "Recuperación", 0.0),
    ("Z2", "Resistencia aeróbica", 0.81),
    ("Z3", "Tempo", 0.90),
    ("Z4", "Subumbral", 0.94),
    ("Z5a", "Supraumbral", 1.00),
    ("Z5b", "Capacidad aeróbica", 1.03),
    ("Z5c", "Potencia anaeróbica", 1.06),
)

# Friel, carrera: Z1 <85 %, Z2 85-89 %, Z3 90-94 %, Z4 95-99 %, Z5a 100-102 %,
# Z5b 103-106 %, Z5c >106 % del LTHR.
_FRIEL_HR_RUNNING: tuple[tuple[str, str, float], ...] = (
    ("Z1", "Recuperación", 0.0),
    ("Z2", "Resistencia aeróbica", 0.85),
    ("Z3", "Tempo", 0.90),
    ("Z4", "Subumbral", 0.95),
    ("Z5a", "Supraumbral", 1.00),
    ("Z5b", "Capacidad aeróbica", 1.03),
    ("Z5c", "Potencia anaeróbica", 1.06),
)


def _check_threshold(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} debe ser un número positivo")


def _build(threshold: float, table: tuple[tuple[str, str, float], ...]) -> tuple[Zone, ...]:
    zones: list[Zone] = []
    for i, (code, name, low_frac) in enumerate(table):
        high = threshold * table[i + 1][2] if i + 1 < len(table) else None
        zones.append(Zone(i + 1, code, name, threshold * low_frac, high))
    return tuple(zones)


def power_zones(ftp_w: float) -> tuple[Zone, ...]:
    """Las 7 zonas de potencia de Coggan, en vatios, a partir del FTP."""
    _check_threshold("ftp_w", ftp_w)
    return _build(ftp_w, _COGGAN_POWER)


def hr_zones(lthr_bpm: float, sport: HrZoneSport = HrZoneSport.CYCLING) -> tuple[Zone, ...]:
    """Las 7 zonas de FC de Friel (Z1-Z5c), en ppm, a partir del LTHR."""
    _check_threshold("lthr_bpm", lthr_bpm)
    table = _FRIEL_HR_RUNNING if sport is HrZoneSport.RUNNING else _FRIEL_HR_CYCLING
    return _build(lthr_bpm, table)


def zone_for(value: float, zones: Sequence[Zone]) -> Zone:
    """Zona que contiene ``value``. Los límites pertenecen a la zona superior."""
    if not math.isfinite(value) or value < 0:
        raise ValueError("el valor debe ser un número no negativo")
    for zone in zones:
        if zone.contains(value):
            return zone
    raise ValueError("el valor no cae en ninguna zona")
