"""Schemas del perfil del atleta, sus umbrales (con zonas calculadas) y su disponibilidad.

Los rangos replican las restricciones CHECK de `app/models/athlete.py`.
"""

from datetime import date, datetime
from typing import Annotated, Any, Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.metrics.zones import (
    HrZoneSport,
    Zone,
    hr_zones,
    pace_zones,
    power_zones,
    trail_hr_zones,
)
from app.models.athlete import PreferredTime, Sex, ThresholdSource
from app.models.common import Sport

# --- Tipos comunes ---------------------------------------------------------------------------


def _check_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("zona horaria IANA no válida (p. ej. 'Europe/Madrid')") from exc
    return value


def _check_unique(values: list[Sport]) -> list[Sport]:
    if len(set(values)) != len(values):
        raise ValueError("los deportes no pueden repetirse")
    return values


Timezone = Annotated[str, Field(min_length=1, max_length=64), AfterValidator(_check_timezone)]
SportList = Annotated[list[Sport], Field(max_length=len(Sport)), AfterValidator(_check_unique)]
HeightCm = Annotated[float, Field(ge=100, le=250, description="Altura en cm (1 decimal).")]
FtpW = Annotated[int, Field(ge=50, le=700, description="FTP en vatios.")]
CyclingLthrBpm = Annotated[
    int, Field(ge=80, le=230, description="FC de umbral láctico en ciclismo (ppm).")
]
RunningLthrBpm = Annotated[
    int,
    Field(ge=80, le=230, description="FC de umbral láctico en carrera (ppm). La usa el trail."),
]
HrMaxBpm = Annotated[int, Field(ge=100, le=240, description="FC máxima (ppm).")]
HrRestBpm = Annotated[int, Field(ge=25, le=120, description="FC en reposo (ppm).")]
PaceSPerKm = Annotated[
    float, Field(ge=120, le=1800, description="Ritmo umbral de carrera en s/km (1 decimal).")
]
Vo2max = Annotated[float, Field(ge=10, le=100, description="VO2máx en ml/kg/min (1 decimal).")]
WeightKg = Annotated[float, Field(ge=25, le=250, description="Peso en kg (2 decimales).")]


# --- Perfil ----------------------------------------------------------------------------------

_PROFILE_EXAMPLE: dict[str, Any] = {
    "user_id": "11111111-2222-3333-4444-555555555555",
    "display_name": "Leti",
    "birth_date": "1990-05-14",
    "sex": "female",
    "height_cm": 168.0,
    "timezone": "Europe/Madrid",
    "sports": ["cycling", "trail_running"],
    "preferences": {"units": "metric", "language": "es"},
    "created_at": "2026-11-01T09:00:00Z",
    "updated_at": "2026-11-15T18:30:00Z",
}


class ProfileOut(BaseModel):
    """Perfil del atleta autenticado. Se crea automáticamente la primera vez que se pide."""

    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"examples": [_PROFILE_EXAMPLE]}
    )

    user_id: UUID
    display_name: str | None
    birth_date: date | None
    sex: Sex | None
    height_cm: float | None
    timezone: str
    sports: list[Sport]
    preferences: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ProfilePatch(BaseModel):
    """Actualización parcial: sólo se cambian los campos enviados.

    `null` borra el valor en los campos opcionales; `timezone`, `sports` y `preferences` no
    admiten `null`. `preferences` se sustituye entero (no se fusiona).
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "display_name": "Leti",
                    "height_cm": 168.0,
                    "sports": ["cycling", "trail_running"],
                },
                {"timezone": "Atlantic/Canary"},
            ]
        },
    )

    display_name: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    birth_date: date | None = None
    sex: Sex | None = None
    height_cm: HeightCm | None = None
    timezone: Timezone | None = None
    sports: SportList | None = None
    preferences: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _non_nullable(self) -> Self:
        for name in ("timezone", "sports", "preferences"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} no admite null")
        if self.birth_date is not None and self.birth_date > date.today():
            raise ValueError("birth_date no puede estar en el futuro")
        return self


# --- Umbrales --------------------------------------------------------------------------------

_THRESHOLD_FIELDS: dict[str, Any] = {
    "effective_from": "2026-11-01",
    "ftp_w": 230,
    "cycling_lthr_bpm": 165,
    "running_lthr_bpm": 172,
    "hr_max_bpm": 186,
    "hr_rest_bpm": 48,
    "threshold_pace_s_per_km": 285.0,
    "vo2max": 52.0,
    "weight_kg": 58.5,
    "source": "test",
    "notes": "Test de 20 min en rodillo.",
}

_THRESHOLD_EXAMPLE: dict[str, Any] = {
    "id": "8d5e2f0a-6b1c-4f3e-9a7d-2c4b6e8f0a1b",
    **_THRESHOLD_FIELDS,
    "legacy_lthr_bpm": None,
    "ftp_proposal_id": None,
    "created_at": "2026-11-01T19:00:00Z",
    "updated_at": "2026-11-01T19:00:00Z",
}


class ThresholdCreate(BaseModel):
    """Nuevo juego de umbrales vigente desde `effective_from` (una fila por fecha).

    Es una foto completa: los valores que no se envían quedan vacíos para esa fecha. La app
    debería precargar el formulario con el umbral vigente. Debe incluir al menos un umbral.

    El LTHR va por disciplina: `cycling_lthr_bpm` (carga por FC de ciclismo) y
    `running_lthr_bpm` (zonas y carga de trail). `legacy_lthr_bpm` es de sólo lectura.
    """

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [_THRESHOLD_FIELDS]})

    effective_from: date
    ftp_w: FtpW | None = None
    cycling_lthr_bpm: CyclingLthrBpm | None = None
    running_lthr_bpm: RunningLthrBpm | None = None
    hr_max_bpm: HrMaxBpm | None = None
    hr_rest_bpm: HrRestBpm | None = None
    threshold_pace_s_per_km: PaceSPerKm | None = None
    vo2max: Vo2max | None = None
    weight_kg: WeightKg | None = None
    source: ThresholdSource = ThresholdSource.MANUAL
    notes: Annotated[str, Field(max_length=2000)] | None = None

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        values = (
            self.ftp_w,
            self.cycling_lthr_bpm,
            self.running_lthr_bpm,
            self.hr_max_bpm,
            self.hr_rest_bpm,
            self.threshold_pace_s_per_km,
            self.vo2max,
            self.weight_kg,
        )
        if all(value is None for value in values):
            raise ValueError("hay que indicar al menos un umbral")
        if (
            self.hr_rest_bpm is not None
            and self.hr_max_bpm is not None
            and self.hr_rest_bpm >= self.hr_max_bpm
        ):
            raise ValueError("hr_rest_bpm debe ser menor que hr_max_bpm")
        for name in ("cycling_lthr_bpm", "running_lthr_bpm"):
            lthr = getattr(self, name)
            if lthr is not None and self.hr_max_bpm is not None and lthr > self.hr_max_bpm:
                raise ValueError(f"{name} no puede ser mayor que hr_max_bpm")
        return self


class ThresholdOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"examples": [_THRESHOLD_EXAMPLE]}
    )

    id: UUID
    effective_from: date
    ftp_w: int | None
    cycling_lthr_bpm: int | None
    running_lthr_bpm: int | None
    legacy_lthr_bpm: int | None = Field(
        description=(
            "LTHR único anterior a la separación por disciplina. Sólo lectura: ningún cálculo"
            " lo usa; está para decidir a qué disciplina pertenecía."
        ),
        json_schema_extra={"readOnly": True},
    )
    hr_max_bpm: int | None
    hr_rest_bpm: int | None
    threshold_pace_s_per_km: float | None
    vo2max: float | None
    weight_kg: float | None
    source: ThresholdSource
    notes: str | None
    ftp_proposal_id: UUID | None = Field(
        description=(
            "Propuesta de test de la que sale `ftp_w`, si se aceptó una. Puede ir con"
            " `source = manual` si el test sólo actualizó el FTP de una fila existente."
        ),
        json_schema_extra={"readOnly": True},
    )
    created_at: datetime
    updated_at: datetime


class ZoneOut(BaseModel):
    """Zona `[low, high)` tal como la calcula `app.metrics.zones.Zone`.

    Unidades: vatios en las zonas de potencia, ppm en las de FC y s/km en las de ritmo.
    `high` null: sin límite. En las de ritmo un número mayor es más lento: `low` es el límite
    rápido (incluido) y `high` el lento (excluido), así que la Z1 no tiene `high`.
    """

    model_config = ConfigDict(from_attributes=True)

    number: int = Field(ge=1, description="Posición de la zona (1 = la más suave).")
    code: str = Field(
        description="Código: Z1…Z7 (potencia), Z1…Z5c (FC de 7 zonas) o Z1…Z5 (5 zonas)."
    )
    name: str
    low: float
    high: float | None

    @classmethod
    def from_zone(cls, zone: Zone) -> "ZoneOut":
        return cls.model_validate(zone)


def _example_zones(zones: tuple[Zone, ...]) -> list[dict[str, Any]]:
    """Ejemplo generado con el propio motor de zonas, para que nunca se desincronice."""
    return [
        {
            "number": zone.number,
            "code": zone.code,
            "name": zone.name,
            "low": round(zone.low, 1),
            "high": None if zone.high is None else round(zone.high, 1),
        }
        for zone in zones
    ]


class ZonesOut(BaseModel):
    """Zonas calculadas a partir del umbral vigente. Null si falta el umbral correspondiente.

    Referencia de cada disciplina: `power` (ciclismo), `running_pace` (carrera) y `trail_hr`
    (trail).

    - `power`: 7 zonas de Coggan sobre `ftp_w` (W).
    - `running_pace`: 5 zonas de ritmo de Friel sobre `threshold_pace_s_per_km` (s/km; la app
      lo muestra en min/km).
    - `trail_hr`: 5 zonas de FC de Friel sobre `running_lthr_bpm` (ppm).
    - `hr_cycling`: 7 zonas de Friel sobre `cycling_lthr_bpm` (ppm). Las usa la carga por FC de
      ciclismo; la app no las muestra.
    - `hr_running`: 7 zonas de Friel (tabla de carrera) sobre `running_lthr_bpm` (ppm).
    """

    power: list[ZoneOut] | None
    running_pace: list[ZoneOut] | None
    trail_hr: list[ZoneOut] | None
    hr_cycling: list[ZoneOut] | None
    hr_running: list[ZoneOut] | None


_CURRENT_EXAMPLE: dict[str, Any] = {
    "on": "2026-11-17",
    "threshold": _THRESHOLD_EXAMPLE,
    "zones": {
        "power": _example_zones(power_zones(230)),
        "running_pace": _example_zones(pace_zones(285.0)),
        "trail_hr": _example_zones(trail_hr_zones(172)),
        "hr_cycling": _example_zones(hr_zones(165, HrZoneSport.CYCLING)),
        "hr_running": _example_zones(hr_zones(172, HrZoneSport.RUNNING)),
    },
}


class CurrentThresholdOut(BaseModel):
    """Umbral vigente en la fecha `on` (la fila más reciente con `effective_from <= on`)."""

    model_config = ConfigDict(json_schema_extra={"examples": [_CURRENT_EXAMPLE]})

    on: date
    threshold: ThresholdOut
    zones: ZonesOut


# --- Disponibilidad --------------------------------------------------------------------------


class AvailabilityDay(BaseModel):
    """Disponibilidad habitual de un día de la semana (0 = lunes … 6 = domingo)."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    weekday: int = Field(ge=0, le=6)
    max_minutes: int | None = Field(
        default=None, ge=0, le=1440, description="Minutos disponibles; null = sin límite fijado."
    )
    sports: SportList = Field(default_factory=list)
    preferred_time: PreferredTime = PreferredTime.ANY
    is_preferred_rest: bool = False


_WEEK_EXAMPLE: dict[str, Any] = {
    "days": [
        {
            "weekday": weekday,
            "max_minutes": minutes,
            "sports": sports,
            "preferred_time": preferred_time,
            "is_preferred_rest": minutes == 0,
        }
        for weekday, minutes, sports, preferred_time in (
            (0, 0, [], "any"),
            (1, 60, ["running"], "morning"),
            (2, 90, ["cycling"], "evening"),
            (3, 60, ["running", "strength"], "morning"),
            (4, 45, ["cycling"], "evening"),
            (5, 240, ["cycling"], "morning"),
            (6, 180, ["trail_running"], "morning"),
        )
    ]
}


class WeekAvailability(BaseModel):
    """Los 7 días de la semana, ordenados de lunes (0) a domingo (6).

    En `GET` siempre vienen los 7 (con valores por defecto si el atleta no los ha rellenado).
    En `PUT` hay que enviar los 7 y se sustituye la semana entera.
    """

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [_WEEK_EXAMPLE]})

    days: list[AvailabilityDay] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def _one_per_weekday(self) -> Self:
        if sorted(day.weekday for day in self.days) != list(range(7)):
            raise ValueError("hay que enviar un elemento por cada día de la semana (0-6)")
        self.days.sort(key=lambda day: day.weekday)
        return self
