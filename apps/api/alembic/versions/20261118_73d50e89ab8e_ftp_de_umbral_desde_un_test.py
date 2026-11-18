"""FTP de umbral desde un test (#45): `athlete_thresholds.ftp_proposal_id`.

Columna nullable sin valor por defecto (sólo cambia el catálogo, no reescribe la tabla) y FK a
`threshold_proposals` con ON DELETE SET NULL. Registra la propuesta de test de la que sale el
`ftp_w` de la fila, tanto si aceptarla creó la fila como si sólo actualizó su FTP. No toca
ningún dato, ningún umbral ni ninguna carga. RLS y privilegios de la tabla no cambian.

Revision ID: 73d50e89ab8e
Revises: 659dc8e0123e
Create Date: 2026-11-18 21:56:17.236969+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "73d50e89ab8e"
down_revision: str | None = "659dc8e0123e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("athlete_thresholds", sa.Column("ftp_proposal_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_athlete_thresholds_ftp_proposal_id_threshold_proposals"),
        "athlete_thresholds",
        "threshold_proposals",
        ["ftp_proposal_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_athlete_thresholds_ftp_proposal_id_threshold_proposals"),
        "athlete_thresholds",
        type_="foreignkey",
    )
    op.drop_column("athlete_thresholds", "ftp_proposal_id")
