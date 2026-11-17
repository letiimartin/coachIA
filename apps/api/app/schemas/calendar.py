"""Schemas del calendario: eventos y, si el evento es una carrera, sus datos (`race`).

Los rangos replican las restricciones de `app/models/calendar.py`.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import AnyHttpUrl, AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.calendar import (
    EnrichmentStatus,
    EventKind,
    RaceDiscipline,
    RacePriority,
    TrainingImpact,
)

MAX_RANGE_DAYS = 366

Title = Annotated[str, Field(min_length=1, max_length=200)]
Notes = Annotated[str, Field(max_length=5000)]
DistanceM = Annotated[float, Field(ge=0, lt=100_000_000, description="Distancia en metros.")]
AscentM = Annotated[float, Field(ge=0, lt=1_000_000, description="Desnivel positivo en metros.")]
Goal = Annotated[str, Field(max_length=2000)]
SourceUrl = Annotated[AnyHttpUrl, Field(max_length=2048, description="Web oficial de la carrera.")]


# --- Carrera ---------------------------------------------------------------------------------

_RACE_IN_EXAMPLE: dict[str, Any] = {
    "discipline": "trail_running",
    "distance_m": 42000.0,
    "ascent_m": 2400.0,
    "priority": "A",
    "goal": "Terminar por debajo de 6 h.",
    "source_url": "https://example.com/carrera",
}


class RaceCreate(BaseModel):
    """Datos de la carrera. Todos opcionales: se pueden completar más tarde."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [_RACE_IN_EXAMPLE]})

    discipline: RaceDiscipline | None = None
    distance_m: DistanceM | None = None
    ascent_m: AscentM | None = None
    priority: RacePriority = RacePriority.B
    goal: Goal | None = None
    source_url: SourceUrl | None = None


class RacePatch(BaseModel):
    """Actualización parcial de la carrera. `null` borra el valor (salvo `priority` y
    `enrichment_status`, que no lo admiten).

    `enrichment_status` permite al atleta confirmar (`confirmed`) los datos completados
    automáticamente (`pending_review`).
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"priority": "B", "enrichment_status": "confirmed"}]},
    )

    discipline: RaceDiscipline | None = None
    distance_m: DistanceM | None = None
    ascent_m: AscentM | None = None
    priority: RacePriority | None = None
    goal: Goal | None = None
    source_url: SourceUrl | None = None
    enrichment_status: EnrichmentStatus | None = None

    @model_validator(mode="after")
    def _non_nullable(self) -> Self:
        for name in ("priority", "enrichment_status"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} no admite null")
        return self


class RaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    discipline: RaceDiscipline | None
    distance_m: float | None
    ascent_m: float | None
    priority: RacePriority
    goal: str | None
    enrichment_status: EnrichmentStatus
    source_url: str | None


# --- Eventos ---------------------------------------------------------------------------------

_EVENT_CREATE_EXAMPLES: list[Any] = [
    {
        "kind": "race",
        "title": "Trail de la Sierra",
        "start_at": "2027-04-18T07:00:00+02:00",
        "all_day": False,
        "training_impact": "none",
        "race": _RACE_IN_EXAMPLE,
    },
    {
        "kind": "travel",
        "title": "Viaje de trabajo a Lisboa",
        "start_at": "2026-12-02T00:00:00+01:00",
        "end_at": "2026-12-04T23:59:00+01:00",
        "all_day": True,
        "training_impact": "reduce",
        "notes": "Hotel con gimnasio.",
    },
]

_EVENT_OUT_EXAMPLE: dict[str, Any] = {
    "id": "3f2a1b4c-5d6e-4f70-8a9b-0c1d2e3f4a5b",
    "kind": "race",
    "title": "Trail de la Sierra",
    "start_at": "2027-04-18T05:00:00Z",
    "end_at": None,
    "all_day": False,
    "training_impact": "none",
    "notes": None,
    "details": {},
    "race": {**_RACE_IN_EXAMPLE, "enrichment_status": "none"},
    "created_at": "2026-11-17T10:00:00Z",
    "updated_at": "2026-11-17T10:00:00Z",
}


def _check_race_kind(kind: EventKind | None, race: object) -> None:
    if race is not None and kind is not None and kind is not EventKind.RACE:
        raise ValueError("race sólo se admite en eventos de tipo 'race'")


class CalendarEventCreate(BaseModel):
    """Nuevo evento. Las fechas deben llevar zona horaria (ISO 8601 con desfase).

    Si `kind` es `race` y no se envía `race`, se crea la carrera con los valores por defecto.
    """

    model_config = ConfigDict(
        extra="forbid", json_schema_extra={"examples": _EVENT_CREATE_EXAMPLES}
    )

    kind: EventKind
    title: Title
    start_at: AwareDatetime
    end_at: AwareDatetime | None = None
    all_day: bool = True
    training_impact: TrainingImpact = TrainingImpact.NONE
    notes: Notes | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    race: RaceCreate | None = None

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        if self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("end_at no puede ser anterior a start_at")
        _check_race_kind(self.kind, self.race)
        return self


class CalendarEventPatch(BaseModel):
    """Actualización parcial de un evento: sólo se cambian los campos enviados.

    - `end_at` y `notes` admiten `null` para borrarlos; el resto de campos no.
    - `race` se fusiona con los datos de carrera existentes (ver `RacePatch`).
    - Si `kind` deja de ser `race`, se borran los datos de la carrera.
    - La coherencia `end_at >= start_at` se comprueba con el evento resultante (409 si no).
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"title": "Trail de la Sierra (42K)", "race": {"priority": "A"}},
                {"training_impact": "no_training"},
            ]
        },
    )

    kind: EventKind | None = None
    title: Title | None = None
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    all_day: bool | None = None
    training_impact: TrainingImpact | None = None
    notes: Notes | None = None
    details: dict[str, Any] | None = None
    race: RacePatch | None = None

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        nullable = {"end_at", "notes"}
        for name in self.model_fields_set - nullable:
            if getattr(self, name) is None:
                raise ValueError(f"{name} no admite null")
        if self.start_at is not None and self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("end_at no puede ser anterior a start_at")
        _check_race_kind(self.kind, self.race)
        return self


class CalendarEventOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"examples": [_EVENT_OUT_EXAMPLE]}
    )

    id: UUID
    kind: EventKind
    title: str
    start_at: datetime
    end_at: datetime | None
    all_day: bool
    training_impact: TrainingImpact
    notes: str | None
    details: dict[str, Any]
    race: RaceOut | None = Field(description="Sólo en eventos de tipo 'race'.")
    created_at: datetime
    updated_at: datetime


class CalendarRange(BaseModel):
    """Rango de fechas (ambas incluidas, en la zona horaria del atleta) para listar eventos.

    Devuelve, ordenados por `start_at`, los eventos que se solapan con el rango. No se pagina:
    el rango máximo es de 366 días.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: date = Field(alias="from", description="Primer día del rango (incluido).")
    to: date = Field(description="Último día del rango (incluido).")

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        if self.to < self.from_:
            raise ValueError("'to' no puede ser anterior a 'from'")
        if self.to - self.from_ >= timedelta(days=MAX_RANGE_DAYS):
            raise ValueError(f"el rango no puede superar {MAX_RANGE_DAYS} días")
        return self
