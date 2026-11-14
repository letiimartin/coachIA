"""Revoca los privilegios de los roles del Data API de Supabase (anon, authenticated).

Segunda capa de seguridad además de RLS: la app accede a los datos sólo a través de la API.
También cambia los privilegios por defecto para que las tablas futuras nazcan sin ellos.
Si los roles no existen (Postgres sin Supabase), no hace nada.

Revision ID: afbd4f3d38f8
Revises: 2ec7b3366a10
Create Date: 2026-11-14 18:32:02.793681+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "afbd4f3d38f8"
down_revision: str | None = "2ec7b3366a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DATA_API_ROLES = ("anon", "authenticated")


def upgrade() -> None:
    # Los nombres de rol son constantes del módulo, no entrada de usuario.
    for role in DATA_API_ROLES:
        op.execute(
            f"""
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role};
                REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {role};
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {role};
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {role};
              END IF;
            END $$;
            """
        )


def downgrade() -> None:
    # Intencionadamente vacío: volver a exponer las tablas al Data API no es un rollback seguro.
    pass
