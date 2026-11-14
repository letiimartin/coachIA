"""Configuración tipada de la API, leída de variables de entorno o de un fichero .env."""

from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["local", "test", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # El .env de la raíz del monorepo y, con prioridad, el de apps/api.
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = "local"
    log_level: str = "INFO"
    # Lista separada por comas: "https://app.coachia.es,http://localhost:8081"
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    database_url: SecretStr | None = None

    # Supabase Auth. Los proyectos nuevos firman los JWT con claves asimétricas (JWKS);
    # supabase_jwt_secret sólo hace falta para proyectos con el secreto HS256 heredado.
    supabase_url: str | None = None
    supabase_jwt_secret: SecretStr | None = None
    supabase_jwt_audience: str = "authenticated"

    # Clave para los endpoints /internal/* (n8n y otras automatizaciones).
    internal_api_key: SecretStr | None = None

    strava_verify_token: SecretStr | None = None

    # Cifrado de tokens OAuth en BD (clave Fernet: `uv run python -m app.core.crypto`).
    token_encryption_key: SecretStr | None = None
    # Firma del parámetro `state` de OAuth (cualquier cadena aleatoria larga).
    oauth_state_secret: SecretStr | None = None

    # Wahoo Cloud API. La redirect URI debe coincidir con una de las registradas en Wahoo.
    wahoo_client_id: str | None = None
    wahoo_client_secret: SecretStr | None = None
    wahoo_redirect_uri: str = "https://letismartcoach.onrender.com/auth/wahoo/callback"
    wahoo_api_base_url: str = "https://api.wahooligan.com"
    wahoo_scopes: str = "user_read workouts_read workouts_write plans_read plans_write"

    # A dónde vuelve el usuario tras conectar una integración.
    app_return_url_mobile: str = "letismartcoach://integrations"
    app_return_url_web: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("supabase_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str | None) -> str | None:
        return value.rstrip("/") if value else value

    @field_validator("database_url", mode="before")
    @classmethod
    def _use_psycopg_driver(cls, value: object) -> object:
        """Supabase entrega URLs `postgresql://`; SQLAlchemy necesita el driver psycopg 3."""
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        if isinstance(raw, str):
            for prefix in ("postgres://", "postgresql://"):
                if raw.startswith(prefix):
                    return "postgresql+psycopg://" + raw.removeprefix(prefix)
        return value

    @model_validator(mode="after")
    def _require_production_settings(self) -> Self:
        if self.environment == "production":
            missing = [
                name
                for name in (
                    "database_url",
                    "supabase_url",
                    "internal_api_key",
                    "token_encryption_key",
                    "oauth_state_secret",
                )
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"Faltan variables obligatorias en producción: {missing}")
        return self

    @property
    def wahoo_configured(self) -> bool:
        return bool(
            self.wahoo_client_id
            and self.wahoo_client_secret
            and self.token_encryption_key
            and self.oauth_state_secret
        )

    @property
    def supabase_issuer(self) -> str | None:
        return f"{self.supabase_url}/auth/v1" if self.supabase_url else None

    @property
    def supabase_jwks_url(self) -> str | None:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json" if self.supabase_url else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
