"""Mapeo puro de un workout de Wahoo a los valores de una fila de `activities`.

Campos según la documentación oficial (https://cloud-api.wahooligan.com):
- workout: id, starts, minutes, name, workout_type_id, workout_summary…
- workout_summary (todos los números llegan como cadenas decimales):
  ascent_accum (m), cadence_avg (rpm), calories_accum (kcal), distance_accum (m),
  duration_active_accum / duration_paused_accum / duration_total_accum (s),
  heart_rate_avg (ppm), power_avg (W), power_bike_np_last (W), power_bike_tss_last,
  speed_avg (m/s), work_accum (J), time_zone, manual, edited, fitness_app_id, file.url.

La documentación no incluye FC máxima, así que `max_hr` queda vacío. Sólo se rellenan datos
brutos: `load`, `load_method` e `intensity_factor` los calcula el motor de métricas, por lo que
`power_bike_tss_last` no se usa (queda en `raw`).

Fuerza (#32): Wahoo no tiene un tipo de fuerza. Sólo `WORKOUT` (42, familia GYM) se mapea a
`strength`. De una actividad de fuerza se guarda sólo lo que llega (duración, FC, calorías):
Wahoo no da ejercicios, series, pesos ni RPE, así que su carga `session_rpe` queda vacía.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.models import Sport

# workout_type_id → (deporte, subdeporte). Tabla "Workout Types" de la documentación.
WORKOUT_TYPES: dict[int, tuple[Sport, str]] = {
    0: (Sport.CYCLING, "biking"),
    1: (Sport.RUNNING, "running"),
    2: (Sport.OTHER, "fe"),
    3: (Sport.RUNNING, "running_track"),
    4: (Sport.TRAIL_RUNNING, "running_trail"),
    5: (Sport.RUNNING, "running_treadmill"),
    6: (Sport.OTHER, "walking"),
    7: (Sport.OTHER, "walking_speed"),
    8: (Sport.OTHER, "walking_nordic"),
    9: (Sport.HIKING, "hiking"),
    10: (Sport.HIKING, "mountaineering"),
    11: (Sport.CYCLING, "biking_cyclecross"),
    12: (Sport.CYCLING, "biking_indoor"),
    13: (Sport.CYCLING, "biking_mountain"),
    14: (Sport.CYCLING, "biking_recumbent"),
    15: (Sport.CYCLING, "biking_road"),
    16: (Sport.CYCLING, "biking_track"),
    17: (Sport.OTHER, "biking_motocycling"),
    18: (Sport.OTHER, "fe_general"),
    19: (Sport.RUNNING, "fe_treadmill"),
    20: (Sport.OTHER, "fe_elliptical"),
    21: (Sport.CYCLING, "fe_bike"),
    22: (Sport.OTHER, "fe_rower"),
    23: (Sport.OTHER, "fe_climber"),
    25: (Sport.SWIMMING, "swimming_lap"),
    26: (Sport.SWIMMING, "swimming_open_water"),
    27: (Sport.OTHER, "snowboarding"),
    28: (Sport.OTHER, "skiing"),
    29: (Sport.OTHER, "skiing_downhill"),
    30: (Sport.OTHER, "skiing_cross_country"),
    31: (Sport.OTHER, "skating"),
    32: (Sport.OTHER, "skating_ice"),
    33: (Sport.OTHER, "skating_inline"),
    34: (Sport.OTHER, "long_boarding"),
    35: (Sport.OTHER, "sailing"),
    36: (Sport.OTHER, "windsurfing"),
    37: (Sport.OTHER, "canoeing"),
    38: (Sport.OTHER, "kayaking"),
    39: (Sport.OTHER, "rowing"),
    40: (Sport.OTHER, "kiteboarding"),
    41: (Sport.OTHER, "stand_up_paddle_board"),
    # WORKOUT (familia GYM): la sesión de gimnasio genérica, la única que puede ser de fuerza.
    # La documentación no tiene ningún tipo de fuerza propio; el resto de la familia GYM
    # (elíptica, remo, clase de cardio, escaladora, yoga) y los `fe_*` no son fuerza.
    42: (Sport.STRENGTH, "workout"),
    43: (Sport.OTHER, "cardio_class"),
    44: (Sport.OTHER, "stair_climber"),
    45: (Sport.OTHER, "wheelchair"),
    46: (Sport.OTHER, "golfing"),
    47: (Sport.OTHER, "other"),
    49: (Sport.CYCLING, "biking_indoor_cycling_class"),
    56: (Sport.OTHER, "walking_treadmill"),
    61: (Sport.CYCLING, "biking_indoor_trainer"),
    62: (Sport.OTHER, "multisport"),
    63: (Sport.OTHER, "transition"),
    64: (Sport.CYCLING, "ebiking"),
    65: (Sport.OTHER, "tickr_offline"),
    66: (Sport.OTHER, "yoga"),
    67: (Sport.RUNNING, "running_race"),
    68: (Sport.CYCLING, "biking_indoor_virtual"),
    69: (Sport.OTHER, "mental_strength"),
    70: (Sport.CYCLING, "handcycling"),
    71: (Sport.RUNNING, "running_indoor_virtual"),
}
UNKNOWN_WORKOUT_TYPE = (Sport.OTHER, "unknown")

_ONE_DECIMAL = Decimal("0.1")
_THREE_DECIMALS = Decimal("0.001")


class WahooMappingError(ValueError):
    """El workout no tiene los datos mínimos para crear una actividad (id o inicio)."""


@dataclass(frozen=True, slots=True)
class MappedActivity:
    external_id: str
    values: dict[str, Any]
    """Columnas de `activities` (sin user_id ni source)."""


def sport_for(workout_type_id: Any) -> tuple[Sport, str]:
    try:
        return WORKOUT_TYPES.get(int(workout_type_id), UNKNOWN_WORKOUT_TYPE)
    except (TypeError, ValueError):
        return UNKNOWN_WORKOUT_TYPE


def map_workout(workout: dict[str, Any], summary: dict[str, Any]) -> MappedActivity:
    """Convierte un workout con su resumen en los valores de una fila de `activities`.

    `raw` guarda el workout original con el resumen incrustado en `workout_summary`.
    """
    workout_id = workout.get("id")
    if workout_id is None or str(workout_id).strip() == "":
        raise WahooMappingError("Workout sin id")
    start_at = parse_datetime(workout.get("starts"))
    if start_at is None:
        raise WahooMappingError(f"Workout {workout_id} sin fecha de inicio válida")

    sport, sub_sport = sport_for(workout.get("workout_type_id"))
    title = workout.get("name") or summary.get("name")
    timezone = summary.get("time_zone")

    values: dict[str, Any] = {
        "sport": sport,
        "sub_sport": sub_sport,
        "title": str(title)[:200] if title else None,
        "start_at": start_at,
        "timezone": str(timezone)[:64] if timezone else None,
        "elapsed_s": _int(summary.get("duration_total_accum")),
        "moving_s": _int(summary.get("duration_active_accum")),
        "distance_m": _decimal(summary.get("distance_accum"), _ONE_DECIMAL),
        "ascent_m": _decimal(summary.get("ascent_accum"), _ONE_DECIMAL),
        "calories": _int(summary.get("calories_accum")),
        # Un 0 en sensores (FC, potencia, cadencia) significa "sin sensor", no un valor real.
        "avg_hr": _positive_int(summary.get("heart_rate_avg")),
        "max_hr": None,
        "avg_power_w": _positive_int(summary.get("power_avg")),
        "normalized_power_w": _positive_int(summary.get("power_bike_np_last")),
        "avg_cadence": _positive_int(summary.get("cadence_avg")),
        "avg_speed_mps": _decimal(summary.get("speed_avg"), _THREE_DECIMALS),
        "raw": {**workout, "workout_summary": summary},
    }
    return MappedActivity(external_id=str(workout_id), values=values)


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    if not number.is_finite() or number < 0:
        return None
    return number


def _decimal(value: Any, quantum: Decimal) -> Decimal | None:
    number = _to_decimal(value)
    return number.quantize(quantum, rounding=ROUND_HALF_UP) if number is not None else None


def _int(value: Any) -> int | None:
    number = _to_decimal(value)
    return int(number.quantize(Decimal(1), rounding=ROUND_HALF_UP)) if number is not None else None


def _positive_int(value: Any) -> int | None:
    number = _int(value)
    return number if number else None
