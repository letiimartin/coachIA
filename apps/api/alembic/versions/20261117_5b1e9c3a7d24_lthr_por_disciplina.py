"""LTHR por disciplina y base de la carga de fuerza (#22).

- `lthr_bpm` pasa a llamarse `legacy_lthr_bpm`. **No se copia a ninguna disciplina**: la autora
  decide fila a fila a cuál pertenecía (`scripts/assign_legacy_lthr.py`).
- Columnas nuevas `cycling_lthr_bpm` y `running_lthr_bpm`, nullable y con el mismo CHECK.
- `activities.rpe` (RPE de la sesión, 1-10, nullable, sin valor por defecto).
- `activities.load_method` admite `session_rpe` (carga de fuerza): se sustituye su CHECK.

No recalcula ninguna carga. El downgrade borra las columnas nuevas (y lo que se haya asignado
en ellas), devuelve `legacy_lthr_bpm` a `lthr_bpm` y vacía la carga de las actividades con
`session_rpe` (salía del `rpe` que se borra y el CHECK antiguo no la admite).

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
ACTIVITIES = "activities"
OLD_LOAD_METHODS = ("power", "heart_rate", "pace", "rpe")
NEW_LOAD_METHODS = (*OLD_LOAD_METHODS, "session_rpe")


def _load_method_check(methods: tuple[str, ...]) -> None:
    op.drop_constraint(op.f(f"ck_{ACTIVITIES}_load_method"), ACTIVITIES, type_="check")
    values = ", ".join(f"'{method}'" for method in methods)
    op.create_check_constraint(
        op.f(f"ck_{ACTIVITIES}_load_method"), ACTIVITIES, f"load_method IN ({values})"
    )


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

    op.add_column(ACTIVITIES, sa.Column("rpe", sa.SmallInteger(), nullable=True))
    op.create_check_constraint(
        op.f(f"ck_{ACTIVITIES}_rpe"), ACTIVITIES, "rpe IS NULL OR rpe BETWEEN 1 AND 10"
    )
    _load_method_check(NEW_LOAD_METHODS)


def downgrade() -> None:
    op.execute(
        f"UPDATE {ACTIVITIES} SET load = NULL, load_method = NULL, intensity_factor = NULL"
        " WHERE load_method = 'session_rpe'"
    )
    _load_method_check(OLD_LOAD_METHODS)
    op.drop_constraint(op.f(f"ck_{ACTIVITIES}_rpe"), ACTIVITIES, type_="check")
    op.drop_column(ACTIVITIES, "rpe")
    for discipline in ("running", "cycling"):
        op.drop_constraint(op.f(f"ck_{TABLE}_{discipline}_lthr"), TABLE, type_="check")
        op.drop_column(TABLE, f"{discipline}_lthr_bpm")
    op.execute(f"ALTER TABLE {TABLE} RENAME CONSTRAINT ck_{TABLE}_legacy_lthr TO ck_{TABLE}_lthr")
    op.alter_column(TABLE, "legacy_lthr_bpm", new_column_name="lthr_bpm")
