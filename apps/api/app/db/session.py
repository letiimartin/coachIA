"""Conexión a la base de datos (SQLAlchemy 2, síncrono con psycopg 3)."""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.errors import ServiceUnavailableError


class Database:
    """Envuelve engine y sessionmaker. Si no hay DATABASE_URL, queda sin configurar."""

    def __init__(self, url: str | None):
        self.engine: Engine | None = create_engine(url, pool_pre_ping=True) if url else None
        self._session_factory = (
            sessionmaker(bind=self.engine, expire_on_commit=False) if self.engine else None
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "Database":
        url = settings.database_url.get_secret_value() if settings.database_url else None
        return cls(url)

    @property
    def configured(self) -> bool:
        return self.engine is not None

    def ping(self) -> None:
        if self.engine is None:
            raise ServiceUnavailableError("Base de datos no configurada.")
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def session(self) -> Iterator[Session]:
        if self._session_factory is None:
            raise ServiceUnavailableError("Base de datos no configurada.")
        with self._session_factory() as session:
            yield session

    def dispose(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
