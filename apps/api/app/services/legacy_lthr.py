"""Asignación revisable del LTHR antiguo (`legacy_lthr_bpm`) a una disciplina (#22).

La migración de #22 no reparte los valores históricos: cada fila de `athlete_thresholds`
conserva su LTHR único en `legacy_lthr_bpm` y ningún cálculo lo usa. La autora decide, fila a
fila, si era de ciclismo, de carrera o de ninguna, en un plan explícito (`threshold_id` →
destino). Este módulo valida el plan y lo aplica; lo usa `scripts/assign_legacy_lthr.py`.

- `none` no cambia nada (se deja constancia de que se revisó).
- Asignar copia `legacy_lthr_bpm` en la columna de la disciplina. `legacy_lthr_bpm` se
  conserva, así que se puede repetir y auditar.
- Un plan con algún error no se aplica entero: ni filas que no existan o sin valor antiguo, ni
  destinos que ya tengan otro valor, ni filas repetidas.
- No recalcula ninguna carga: eso es el recálculo histórico (`scripts/recompute_loads.py`).
"""

import enum
import uuid
from collections.abc import Iterable
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models import AthleteThreshold


class LegacyTarget(enum.StrEnum):
    CYCLING = "cycling"
    RUNNING = "running"
    NONE = "none"


_COLUMN: dict[LegacyTarget, str] = {
    LegacyTarget.CYCLING: "cycling_lthr_bpm",
    LegacyTarget.RUNNING: "running_lthr_bpm",
}


@dataclass(frozen=True, slots=True)
class Assignment:
    threshold_id: uuid.UUID
    target: LegacyTarget


@dataclass(frozen=True, slots=True)
class PlannedChange:
    threshold_id: uuid.UUID
    user_id: uuid.UUID
    effective_from: str
    legacy_lthr_bpm: int
    target: LegacyTarget
    column: str | None
    already_applied: bool


class LegacyPlanError(ValueError):
    """El plan no se puede aplicar. `errors` lista los motivos, uno por fila."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def pending_rows(session: Session) -> list[AthleteThreshold]:
    """Filas con LTHR antiguo, por atleta y fecha, para revisarlas."""
    return list(
        session.scalars(
            sa.select(AthleteThreshold)
            .where(AthleteThreshold.legacy_lthr_bpm.is_not(None))
            .order_by(AthleteThreshold.user_id, AthleteThreshold.effective_from)
        )
    )


def plan_changes(session: Session, assignments: Iterable[Assignment]) -> list[PlannedChange]:
    """Valida el plan sin escribir nada. `LegacyPlanError` si alguna fila no es válida."""
    assignments = list(assignments)
    errors: list[str] = []
    seen: set[uuid.UUID] = set()
    for item in assignments:
        if item.threshold_id in seen:
            errors.append(f"{item.threshold_id}: aparece más de una vez")
        seen.add(item.threshold_id)
    rows = {
        row.id: row
        for row in session.scalars(sa.select(AthleteThreshold).where(AthleteThreshold.id.in_(seen)))
    }
    changes: list[PlannedChange] = []
    for item in assignments:
        row = rows.get(item.threshold_id)
        if row is None:
            errors.append(f"{item.threshold_id}: no existe")
            continue
        if row.legacy_lthr_bpm is None:
            errors.append(f"{item.threshold_id}: no tiene LTHR antiguo")
            continue
        column = _COLUMN.get(item.target)
        current = None if column is None else getattr(row, column)
        if current is not None and current != row.legacy_lthr_bpm:
            errors.append(
                f"{item.threshold_id}: {column} ya vale {current} (antiguo {row.legacy_lthr_bpm})"
            )
            continue
        changes.append(
            PlannedChange(
                row.id,
                row.user_id,
                row.effective_from.isoformat(),
                row.legacy_lthr_bpm,
                item.target,
                column,
                already_applied=column is None or current is not None,
            )
        )
    if errors:
        raise LegacyPlanError(errors)
    return changes


def apply_plan(session: Session, assignments: Iterable[Assignment]) -> list[PlannedChange]:
    """Valida y aplica el plan en la sesión (sin commit: lo hace quien llama)."""
    changes = plan_changes(session, assignments)
    for change in changes:
        if change.column is None or change.already_applied:
            continue
        session.execute(
            sa.update(AthleteThreshold)
            .where(AthleteThreshold.id == change.threshold_id)
            .values({change.column: change.legacy_lthr_bpm})
        )
    session.flush()
    return changes
