import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core.security import TokenVerifier
from app.main import create_app
from tests.conftest import USER_ID, TokenFactory, make_settings


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/v1/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_with_valid_asymmetric_token(client: TestClient, make_token: TokenFactory) -> None:
    response = client.get("/v1/me", headers=_auth(make_token()))

    assert response.status_code == 200
    assert response.json() == {"id": str(USER_ID), "email": "atleta@example.com"}


def test_me_with_valid_legacy_hs256_token(client: TestClient, make_token: TokenFactory) -> None:
    response = client.get("/v1/me", headers=_auth(make_token(algorithm="HS256")))

    assert response.status_code == 200
    assert response.json()["id"] == str(USER_ID)


@pytest.mark.parametrize(
    ("overrides", "expected_message"),
    [
        ({"expires_in": -10}, "La sesión ha caducado."),
        ({"aud": "anon"}, "Token no válido."),
        ({"iss": "https://otro-proyecto.supabase.co/auth/v1"}, "Token no válido."),
        ({"sub": None}, "Token no válido."),
        ({"sub": "no-es-un-uuid"}, "Token no válido."),
    ],
)
def test_invalid_claims_are_rejected(
    client: TestClient,
    make_token: TokenFactory,
    overrides: dict[str, object],
    expected_message: str,
) -> None:
    response = client.get("/v1/me", headers=_auth(make_token(**overrides)))

    assert response.status_code == 401
    assert response.json()["error"]["message"] == expected_message


def test_token_signed_with_another_key_is_rejected(
    client: TestClient, make_token: TokenFactory
) -> None:
    other_key = ec.generate_private_key(ec.SECP256R1())

    response = client.get("/v1/me", headers=_auth(make_token(key=other_key)))

    assert response.status_code == 401


def test_hs256_token_with_wrong_secret_is_rejected(
    client: TestClient, make_token: TokenFactory
) -> None:
    token = make_token(algorithm="HS256", key="another-secret-that-is-long-enough-123456")

    response = client.get("/v1/me", headers=_auth(token))

    assert response.status_code == 401


def test_unsigned_token_is_rejected(client: TestClient, make_token: TokenFactory) -> None:
    response = client.get("/v1/me", headers=_auth(make_token(algorithm="none", key=None)))

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Algoritmo de firma no admitido."


def test_malformed_token_is_rejected(client: TestClient) -> None:
    response = client.get("/v1/me", headers=_auth("esto-no-es-un-jwt"))

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Token mal formado."


def test_hs256_without_configured_secret_is_rejected(make_token: TokenFactory) -> None:
    settings = make_settings(supabase_jwt_secret=None)
    app = create_app(settings, token_verifier=TokenVerifier(settings, jwks_client=None))
    client = TestClient(app)

    response = client.get("/v1/me", headers=_auth(make_token(algorithm="HS256")))

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Verificación de tokens no configurada."
