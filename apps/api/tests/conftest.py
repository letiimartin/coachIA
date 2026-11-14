import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import TokenVerifier
from app.main import create_app

SUPABASE_URL = "https://test-project.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
HS256_SECRET = "test-legacy-jwt-secret-with-enough-length-1234"
INTERNAL_KEY = "internal-test-key"
STRAVA_TOKEN = "strava-verify-token"
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
