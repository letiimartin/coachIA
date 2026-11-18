"""Zonas de entrenamiento calculadas a partir de umbrales (nunca se guardan).

- Potencia: 7 zonas de Andrew Coggan sobre el FTP (Allen y Coggan, *Training and Racing with
  a Power Meter*). Los rangos publicados son Z1 ≤55 %, Z2 56-75 %, Z3 76-90 %, Z4 91-105 %,
  Z5 106-120 %, Z6 121-150 % y Z7 >150 %. Aquí se expresan como intervalos contiguos
  ``[inferior, superior)`` usando el límite superior publicado de cada zona como frontera.
- Frecuencia cardiaca: zonas de Joe Friel sobre el LTHR (*The Cyclist's Training Bible* y
  *The Triathlete's Training Bible*), con tablas distintas para ciclismo y carrera.
- Modelo de 5 zonas de Friel (Z5a-Z5c unidas en Z5): ritmo de carrera sobre el ritmo umbral
  (``pace_zones``) y FC de trail sobre el LTHR de carrera (``trail_hr_zones``).

Cada disciplina tiene una única referencia de zonas, que da ``zone_model_for(sport)``: ciclismo
por potencia, carrera por ritmo y trail por FC. El LTHR que usa cada disciplina (para sus zonas
de FC y para la carga por FC) sale de una sola correspondencia, ``lthr_field_for(sport)``.
"""

import enum
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from app.models.common import Sport


@dataclass(frozen=True, slots=True)
class Zone:
    """Zona ``[low, high)`` en las unidades del umbral (W, ppm o s/km). ``high`` None: sin límite.

    En las zonas de ritmo (s/km) un número mayor es más lento: ``low`` es el límite rápido y
    ``high`` el lento, así que la Z1 (la más lenta) es la que no tiene ``high`` y la Z5 (la más
    rápida) empieza en 0.
    """

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


# Modelo de 5 zonas de Friel. Ritmo de carrera: porcentaje del tiempo por km sobre el ritmo
# umbral (más alto es más lento). Z1 >129 %, Z2 114-129 %, Z3 106-114 %, Z4 100-106 % y
# Z5 <100 %. (código, nombre, fracción inferior, fracción superior o None).
_FRIEL_PACE_RUNNING: tuple[tuple[str, str, float, float | None], ...] = (
    ("Z1", "Recuperación", 1.29, None),
    ("Z2", "Aeróbico", 1.14, 1.29),
    ("Z3", "Tempo", 1.06, 1.14),
    ("Z4", "Umbral", 1.00, 1.06),
    ("Z5", "Por encima del umbral", 0.0, 1.00),
)

# Trail, FC sobre el LTHR de carrera: Z1 <85 %, Z2 85-90 %, Z3 90-95 %, Z4 95-100 % y
# Z5 ≥100 %.
_FRIEL_HR_TRAIL: tuple[tuple[str, str, float], ...] = (
    ("Z1", "Recuperación", 0.0),
    ("Z2", "Aeróbico", 0.85),
    ("Z3", "Tempo", 0.90),
    ("Z4", "Umbral", 0.95),
    ("Z5", "Por encima del umbral", 1.00),
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


def pace_zones(threshold_pace_s_per_km: float) -> tuple[Zone, ...]:
    """Las 5 zonas de ritmo de carrera (Friel), en s/km, a partir del ritmo umbral.

    Ordenadas de Z1 (la más lenta) a Z5 (la más rápida). ``low`` es el límite rápido (incluido)
    y ``high`` el lento (excluido): un ritmo exactamente igual al umbral es Z4 y uno exactamente
    al 129 % es Z1. Son contiguas: ``zones[i].low == zones[i + 1].high``.
    """
    _check_threshold("threshold_pace_s_per_km", threshold_pace_s_per_km)
    return tuple(
        Zone(
            i + 1,
            code,
            name,
            threshold_pace_s_per_km * low_frac,
            None if high_frac is None else threshold_pace_s_per_km * high_frac,
        )
        for i, (code, name, low_frac, high_frac) in enumerate(_FRIEL_PACE_RUNNING)
    )


def trail_hr_zones(running_lthr_bpm: float) -> tuple[Zone, ...]:
    """Las 5 zonas de FC de trail (Friel, Z5a-Z5c unidas), en ppm, sobre el LTHR de carrera."""
    _check_threshold("running_lthr_bpm", running_lthr_bpm)
    return _build(running_lthr_bpm, _FRIEL_HR_TRAIL)


# --- Referencia de zonas y de umbral por disciplina ------------------------------------------


class ZoneKind(enum.StrEnum):
    POWER = "power"
    PACE = "pace"
    HEART_RATE = "heart_rate"


# Columna de `athlete_thresholds` con el LTHR de cada deporte, para sus zonas de FC y para la
# carga por FC. Única correspondencia: un `trail_lthr_bpm` futuro sólo cambia la entrada de
# trail. Los demás deportes no usan ningún LTHR: la fuerza se carga por session RPE, y
# senderismo, natación y otros sólo se registran (``app.metrics.load.LOAD_RULES``).
_LTHR_FIELD: Mapping[Sport, str] = {
    Sport.CYCLING: "cycling_lthr_bpm",
    Sport.RUNNING: "running_lthr_bpm",
    Sport.TRAIL_RUNNING: "running_lthr_bpm",
}


def lthr_field_for(sport: Sport) -> str | None:
    """Columna de `athlete_thresholds` con el LTHR que usa ``sport``; ``None`` si no usa."""
    return _LTHR_FIELD.get(sport)


@dataclass(frozen=True, slots=True)
class ZoneModel:
    """Modelo de zonas de una disciplina y columna de `athlete_thresholds` que lo alimenta."""

    kind: ZoneKind
    threshold_field: str
    unit: str
    build: Callable[[float], tuple[Zone, ...]]

    def zones(self, threshold: float | None) -> tuple[Zone, ...] | None:
        """Zonas para el valor del umbral, o ``None`` si no hay umbral."""
        return None if threshold is None else self.build(threshold)


_ZONE_MODELS: Mapping[Sport, ZoneModel] = {
    Sport.CYCLING: ZoneModel(ZoneKind.POWER, "ftp_w", "W", power_zones),
    Sport.RUNNING: ZoneModel(ZoneKind.PACE, "threshold_pace_s_per_km", "s/km", pace_zones),
    Sport.TRAIL_RUNNING: ZoneModel(
        ZoneKind.HEART_RATE, _LTHR_FIELD[Sport.TRAIL_RUNNING], "bpm", trail_hr_zones
    ),
}


def zone_model_for(sport: Sport) -> ZoneModel | None:
    """Referencia de zonas de cada disciplina. Los demás deportes no tienen zonas (``None``)."""
    return _ZONE_MODELS.get(sport)


def zone_for(value: float, zones: Sequence[Zone]) -> Zone:
    """Zona que contiene ``value``. Los límites pertenecen a la zona superior."""
    if not math.isfinite(value) or value < 0:
        raise ValueError("el valor debe ser un número no negativo")
    for zone in zones:
        if zone.contains(value):
            return zone
    raise ValueError("el valor no cae en ninguna zona")
