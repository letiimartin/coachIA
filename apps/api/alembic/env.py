"""Entorno de Alembic.

- Online:  `uv run alembic upgrade head` (necesita DATABASE_URL).
- Offline: `uv run alembic upgrade head --sql > migration.sql` genera el SQL sin conectarse;
  así se pueden aplicar las migraciones mediante la Management API de Supabase.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  (registra los modelos en Base.metadata)
from alembic import context
from app.core.config import Settings
from app.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Para el modo offline basta con el dialecto; no se conecta a ninguna base de datos.
OFFLINE_FALLBACK_URL = "postgresql+psycopg://offline"


def include_object(
    obj: object, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    """Ignora las FK hacia el esquema auth de Supabase: no forman parte de nuestros modelos."""
    if type_ == "foreign_key_constraint":
        referred = getattr(obj, "referred_table", None)
        if getattr(referred, "schema", None) == "auth":
            return False
    return True


def _database_url() -> str | None:
    settings = Settings()
    return settings.database_url.get_secret_value() if settings.database_url else None


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url() or OFFLINE_FALLBACK_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _database_url()
    if url is None:
        raise RuntimeError("DATABASE_URL no está definida.")
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = url
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
