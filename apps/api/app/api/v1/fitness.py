"""Serie de forma del atleta autenticado: carga diaria y CTL/ATL/TSB (#17).

Los valores salen de `daily_load`, que regenera `services.fitness.recompute_from`. El LLM los
consulta aquí: nunca los calcula.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import error_responses
from app.schemas.fitness import FitnessDayOut, FitnessRange, FitnessSeriesOut
from app.services import fitness

router = APIRouter(prefix="/athlete/fitness", tags=["fitness"])


@router.get("", responses=error_responses())
def get_fitness_series(
    user: CurrentUser, db: DbSession, date_range: Annotated[FitnessRange, Query()]
) -> FitnessSeriesOut:
    """Carga diaria y CTL/ATL/TSB de cada día del rango `[from, to]` (máximo 366 días)."""
    days = fitness.fitness_range(db, user.id, date_range.from_, date_range.to)
    return FitnessSeriesOut(
        from_=date_range.from_,
        to=date_range.to,
        days=[
            FitnessDayOut(
                day=d.day,
                load=round(d.load, 1),
                ctl=round(d.ctl, 1),
                atl=round(d.atl, 1),
                tsb=round(d.tsb, 1),
            )
            for d in days
        ],
    )
