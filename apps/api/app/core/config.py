"""Configuración tipada de la API, leída de variables de entorno o de un fichero .env."""

from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["local", "test", "production"]


class ModelPrice(BaseModel):
    """Precio oficial de un modelo en USD por millón de tokens (MTok).

    `cache_write` es la escritura en la caché de 5 minutos y `cache_read`, la lectura. Si el
    proveedor cobra más a partir de cierto tamaño de prompt, `long_context_over_tokens` es ese
    umbral (tokens de entrada, incluida la caché) y `long_context_multiplier`, el recargo.
    """

    input: Decimal = Field(ge=0)
    output: Decimal = Field(ge=0)
    cache_write: Decimal = Field(ge=0)
    cache_read: Decimal = Field(ge=0)
    long_context_over_tokens: int | None = Field(default=None, gt=0)
    long_context_multiplier: Decimal = Field(default=Decimal(1), ge=1)


# Precios oficiales de Anthropic (https://platform.claude.com/docs/en/about-claude/pricing),
# consultados el 19 de noviembre de 2026. Se pueden sobrescribir con COACH_LLM_PRICES (JSON).
DEFAULT_LLM_PRICES: dict[str, ModelPrice] = {
    "claude-haiku-5-5": ModelPrice(
        input=Decimal("0.10"),
        output=Decimal("0.50"),
        cache_write=Decimal("0.125"),
        cache_read=Decimal("0.01"),
        long_context_over_tokens=100_000,
        long_context_multiplier=Decimal(5),
    ),
    "claude-sonnet-5-5": ModelPrice(
        input=Decimal(2),
        output=Decimal(10),
        cache_write=Decimal("2.50"),
        cache_read=Decimal("0.10"),
    ),
    "claude-opus-5-5": ModelPrice(
        input=Decimal(4), output=Decimal(20), cache_write=Decimal(5), cache_read=Decimal("0.20")
    ),
}


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

    # Coach (#55). Sin la clave del proveedor, el coach no llama al LLM: los endpoints que lo
    # necesitan responden 503 `coach_unavailable` (el filtro de seguridad funciona igual).
    anthropic_api_key: SecretStr | None = None
    # Modelo que conversa: decisión de la autora (#55). Económico, dentro del límite mensual.
    coach_model: str = "claude-haiku-5-5"
    # Modelo de los resúmenes de conversación. Por defecto, el mismo que conversa.
    coach_summary_model: str | None = None
    coach_effort: Literal["low", "medium", "high"] | None = "low"
    coach_max_output_tokens: int = Field(default=1500, ge=256, le=16000)
    # Contexto de cada respuesta: los últimos N mensajes y un resumen de los anteriores, que se
    # actualiza cuando quedan al menos `coach_summary_batch` mensajes fuera de la ventana.
    coach_history_messages: int = Field(default=12, ge=2, le=100)
    coach_summary_batch: int = Field(default=8, ge=1, le=100)
    # Rondas máximas de herramientas en una respuesta.
    coach_max_tool_rounds: int = Field(default=5, ge=1, le=10)
    # Presupuesto mensual (todas las llamadas del mes: conversación, resúmenes, planificador).
    coach_monthly_budget_eur: Decimal = Field(default=Decimal("4.00"), ge=0)
    coach_budget_warning_ratio: Decimal = Field(default=Decimal("0.8"), gt=0, le=1)
    # Cambio USD→EUR para pasar a euros los precios oficiales (en dólares). 1.0 por defecto:
    # sobrestima el coste en euros, así que el límite nunca se queda corto.
    coach_usd_to_eur: Decimal = Field(default=Decimal("1.0"), gt=0)
    coach_llm_prices: dict[str, ModelPrice] = Field(
        default_factory=lambda: dict(DEFAULT_LLM_PRICES)
    )

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
    def coach_configured(self) -> bool:
        return self.anthropic_api_key is not None

    @property
    def supabase_issuer(self) -> str | None:
        return f"{self.supabase_url}/auth/v1" if self.supabase_url else None

    @property
    def supabase_jwks_url(self) -> str | None:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json" if self.supabase_url else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
