"""Schemas de la serie de forma (carga diaria y CTL/ATL/TSB). Contrato: #17."""

from datetime import date, timedelta
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.metrics.fitness import fitness_series

MAX_RANGE_DAYS = 366


class FitnessRange(BaseModel):
    """Rango de fechas (ambas incluidas, días locales del atleta). Máximo 366 días."""

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


class FitnessDayOut(BaseModel):
    """Un día de la serie. Valores redondeados a 1 decimal.

    - `load`: carga total del día (suma del TSS/hrTSS/rTSS de sus actividades, sin duplicados).
    - `ctl`: forma física (media exponencial de 42 días) al final del día.
    - `atl`: fatiga (media exponencial de 7 días) al final del día.
    - `tsb`: frescura con la que se empieza el día: CTL − ATL **del día anterior**
      (criterio de TrainingPeaks).
    """

    day: date
    load: float = Field(ge=0)
    ctl: float = Field(ge=0)
    atl: float = Field(ge=0)
    tsb: float


def _example() -> dict[str, Any]:
    """Ejemplo generado con el propio motor de métricas, para que nunca se desincronice."""
    start = date(2026, 11, 10)
    loads = {start + timedelta(days=i): load for i, load in enumerate((80.0, 0.0, 120.0))}
    days = fitness_series(loads, initial_ctl=55.0, initial_atl=60.0)
    return {
        "from": "2026-11-10",
        "to": "2026-11-12",
        "days": [
            {
                "day": d.day.isoformat(),
                "load": round(d.load, 1),
                "ctl": round(d.ctl, 1),
                "atl": round(d.atl, 1),
                "tsb": round(d.tsb, 1),
            }
            for d in days
        ],
    }


class FitnessSeriesOut(BaseModel):
    """Serie diaria continua (un elemento por día del rango, ordenada por fecha).

    Antes de la primera actividad todo vale 0. Los días sin actividad tienen `load` 0, y los
    días posteriores al último recálculo continúan la serie como descanso.
    """

    model_config = ConfigDict(populate_by_name=True, json_schema_extra={"examples": [_example()]})

    from_: date = Field(alias="from")
    to: date
    days: list[FitnessDayOut]
