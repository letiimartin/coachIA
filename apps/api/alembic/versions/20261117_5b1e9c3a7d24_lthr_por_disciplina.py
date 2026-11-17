"""LTHR por disciplina en `athlete_thresholds` (#22).

- `lthr_bpm` pasa a llamarse `legacy_lthr_bpm`. **No se copia a ninguna disciplina**: la autora
  decide fila a fila a cuál pertenecía (`scripts/assign_legacy_lthr.py`).
- Columnas nuevas `cycling_lthr_bpm` y `running_lthr_bpm`, nullable y con el mismo CHECK.

No recalcula ninguna carga. El downgrade borra las columnas nuevas (y lo que se haya asignado
en ellas) y devuelve `legacy_lthr_bpm` a `lthr_bpm`.

Revision ID: 5b1e9c3a7d24
Revises: 8d82e2645fa7
Create Date: 2026-11-17 23:50:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5b1e9c3a7d24"
down_revision: str | None = "8d82e2645fa7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "athlete_thresholds"
LTHR_RANGE = "BETWEEN 80 AND 230"


def upgrade() -> None:
    op.alter_column(TABLE, "lthr_bpm", new_column_name="legacy_lthr_bpm")
    op.execute(f"ALTER TABLE {TABLE} RENAME CONSTRAINT ck_{TABLE}_lthr TO ck_{TABLE}_legacy_lthr")
    for discipline in ("cycling", "running"):
        column = f"{discipline}_lthr_bpm"
        op.add_column(TABLE, sa.Column(column, sa.Integer(), nullable=True))
        op.create_check_constraint(
            op.f(f"ck_{TABLE}_{discipline}_lthr"),
            TABLE,
            f"{column} IS NULL OR {column} {LTHR_RANGE}",
        )


def downgrade() -> None:
    for discipline in ("running", "cycling"):
        op.drop_constraint(op.f(f"ck_{TABLE}_{discipline}_lthr"), TABLE, type_="check")
        op.drop_column(TABLE, f"{discipline}_lthr_bpm")
    op.execute(f"ALTER TABLE {TABLE} RENAME CONSTRAINT ck_{TABLE}_legacy_lthr TO ck_{TABLE}_lthr")
    op.alter_column(TABLE, "legacy_lthr_bpm", new_column_name="lthr_bpm")
