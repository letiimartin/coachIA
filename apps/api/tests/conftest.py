import os
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import jwt
import pytest
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.core.security import TokenVerifier
from app.main import create_app

SUPABASE_URL = "https://test-project.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
HS256_SECRET = "test-legacy-jwt-secret-with-enough-length-1234"
INTERNAL_KEY = "internal-test-key"
STRAVA_TOKEN = "strava-verify-token"
FERNET_KEY = "kVr0f8q3B4jCqTSJ7m1zZpX9VbYwLd2N5eHgUoAaQ1c="
STATE_SECRET = "oauth-state-secret-for-tests"
USER_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


@dataclass
class _SigningKey:
    key: Any


class FakeJWKSClient:
    """Sustituye a jwt.PyJWKClient: devuelve siempre la clave pública de prueba."""

    def __init__(self, public_key: Any):
        self.public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> _SigningKey:
        return _SigningKey(self.public_key)


@pytest.fixture(scope="session")
def ec_private_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": "test",
        "supabase_url": SUPABASE_URL,
        "supabase_jwt_secret": HS256_SECRET,
        "internal_api_key": INTERNAL_KEY,
        "strava_verify_token": STRAVA_TOKEN,
        "token_encryption_key": FERNET_KEY,
        "oauth_state_secret": STATE_SECRET,
        "wahoo_client_id": "wahoo-client-id",
        "wahoo_client_secret": "wahoo-client-secret",
        "wahoo_api_base_url": "https://wahoo.test",
        # Explícito: el fixture alembic_config exporta DATABASE_URL durante toda la sesión y,
        # sin esto, las apps de los tests sin BD acabarían conectadas según el orden de ejecución.
        "database_url": None,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def app(settings: Settings, ec_private_key: ec.EllipticCurvePrivateKey) -> FastAPI:
    verifier = TokenVerifier(settings, jwks_client=FakeJWKSClient(ec_private_key.public_key()))
    return create_app(settings, token_verifier=verifier)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


TokenFactory = Callable[..., str]


@pytest.fixture
def make_token(ec_private_key: ec.EllipticCurvePrivateKey) -> TokenFactory:
    def _make(
        *,
        algorithm: str = "ES256",
        key: Any = None,
        expires_in: int = 3600,
        **claim_overrides: Any,
    ) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "sub": str(USER_ID),
            "email": "atleta@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "iss": ISSUER,
            "iat": now,
            "exp": now + expires_in,
        }
        claims.update(claim_overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        if key is None and algorithm != "none":
            key = ec_private_key if algorithm == "ES256" else HS256_SECRET
        return jwt.encode(claims, key, algorithm=algorithm)

    return _make


# --- Base de datos de tests ------------------------------------------------------------------
# TEST_DATABASE_URL debe apuntar a una BD DESECHABLE: se borran y recrean los esquemas public y
# auth. Sin la variable, los tests marcados con requires_db se omiten.

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
requires_db = pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL no definida")

# Replica mínima de lo que Supabase trae de serie: esquema auth y roles del Data API, con
# privilegios por defecto sobre las tablas nuevas de public.
_SUPABASE_BOOTSTRAP = """
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
DROP SCHEMA IF EXISTS auth CASCADE;
CREATE SCHEMA auth;
CREATE TABLE auth.users (id uuid PRIMARY KEY);
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    CREATE ROLE anon NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOLOGIN;
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated;
"""


def database_url_for_tests() -> str:
    assert TEST_DATABASE_URL is not None
    if "supabase" in TEST_DATABASE_URL:
        pytest.fail("TEST_DATABASE_URL no puede apuntar a Supabase: los tests borran datos.")
    return TEST_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)


@pytest.fixture(scope="session")
def alembic_config() -> Iterator[Config]:
    url = database_url_for_tests()
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    yield Config("alembic.ini")
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def engine(alembic_config: Config) -> Iterator[Engine]:
    engine = create_engine(database_url_for_tests())
    with engine.begin() as conn:
        conn.execute(text(_SUPABASE_BOOTSTRAP))
    command.upgrade(alembic_config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def user_id(engine: Engine) -> Iterator[uuid.UUID]:
    """Usuario de Supabase Auth recién creado (sin perfil de atleta todavía)."""
    new_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": new_id})
    yield new_id
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": new_id})


@pytest.fixture
def athlete_id(engine: Engine, user_id: uuid.UUID) -> uuid.UUID:
    """Usuario con perfil de atleta."""
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO athlete_profiles (user_id) VALUES (:id)"), {"id": user_id})
    return user_id


@pytest.fixture
def session(engine: Engine, user_id: uuid.UUID) -> Iterator[Session]:
    # Depende de user_id para cerrarse (rollback) ANTES de borrar el usuario: si no, el DELETE
    # esperaría a los bloqueos de fila de esta sesión.
    with Session(engine) as session:
        yield session
        session.rollback()
