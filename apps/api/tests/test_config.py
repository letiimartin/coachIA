import pytest
from pydantic import ValidationError

from tests.conftest import make_settings


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@db.example.com:5432/postgres",
        "postgres://u:p@db.example.com:5432/postgres",
    ],
)
def test_database_url_uses_psycopg_driver(url: str) -> None:
    settings = make_settings(database_url=url)

    assert settings.database_url is not None
    assert settings.database_url.get_secret_value().startswith("postgresql+psycopg://u:p@")


def test_database_url_is_hidden_in_repr() -> None:
    settings = make_settings(database_url="postgresql://u:supersecreto@host/db")

    assert "supersecreto" not in repr(settings)


def test_cors_origins_accept_comma_separated_string() -> None:
    settings = make_settings(cors_origins="https://a.example, http://localhost:8081 ,")

    assert settings.cors_origins == ["https://a.example", "http://localhost:8081"]


def test_supabase_urls_are_derived_without_trailing_slash() -> None:
    settings = make_settings(supabase_url="https://abc.supabase.co/")

    assert settings.supabase_issuer == "https://abc.supabase.co/auth/v1"
    assert settings.supabase_jwks_url == "https://abc.supabase.co/auth/v1/.well-known/jwks.json"


def test_production_requires_critical_settings() -> None:
    with pytest.raises(ValidationError, match="database_url"):
        make_settings(environment="production", database_url=None)
