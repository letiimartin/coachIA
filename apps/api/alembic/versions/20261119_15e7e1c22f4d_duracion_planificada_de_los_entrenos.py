"""Duración planificada de los entrenos (#52).

Añade `planned_workouts.planned_duration_s`: la duración planificada en segundos, opcional
(null si no se ha definido; no se estima a partir de las series), entre 1 s y 24 h. Las filas
existentes quedan en null. El downgrade borra la columna.

Revision ID: 15e7e1c22f4d
Revises: e4b8468591c1
Create Date: 2026-11-19 20:00:20.435304+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "15e7e1c22f4d"
down_revision: str | None = "e4b8468591c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("planned_workouts", sa.Column("planned_duration_s", sa.Integer(), nullable=True))
    op.create_check_constraint(
        op.f("ck_planned_workouts_planned_duration_s"),
        "planned_workouts",
        "planned_duration_s IS NULL OR planned_duration_s BETWEEN 1 AND 86400",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_planned_workouts_planned_duration_s"), "planned_workouts", type_="check"
    )
    op.drop_column("planned_workouts", "planned_duration_s")
