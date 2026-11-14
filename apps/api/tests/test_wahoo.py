import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.crypto import TokenCipher, TokenCipherError
from app.core.oauth_state import InvalidStateError, OAuthState, OAuthStateSigner
from app.core.security import TokenVerifier
from app.db.session import Database
from app.integrations.wahoo import service
from app.integrations.wahoo.client import WahooAuthError, WahooClient, WahooTokens
from app.main import create_app
from app.models import Integration, IntegrationStatus
from tests.conftest import (
    FERNET_KEY,
    STATE_SECRET,
    FakeJWKSClient,
    TokenFactory,
    database_url_for_tests,
    make_settings,
    requires_db,
)

Handler = Callable[[httpx.Request], httpx.Response]


def _token_response(**overrides: Any) -> httpx.Response:
    body = {
        "access_token": "access-1",
        "refresh_token": "refresh-1",
        "expires_in": 7200,
        "scope": "user_read workouts_read",
    }
    body.update(overrides)
    return httpx.Response(200, json=body)


def _wahoo_client(handler: Handler) -> WahooClient:
    return WahooClient(make_settings(), httpx.Client(transport=httpx.MockTransport(handler)))


def _query(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


# --- Cifrado y state ----------------------------------------------------------------------


def test_token_cipher_roundtrip_and_wrong_key() -> None:
    cipher = TokenCipher(FERNET_KEY)
    encrypted = cipher.encrypt("secreto")

    assert encrypted != "secreto"
    assert cipher.decrypt(encrypted) == "secreto"
    other = TokenCipher("Zx9yW8vU7tS6rQ5pO4nM3lK2jI1hG0fE9dC8bA7z6Y4=")
    with pytest.raises(TokenCipherError):
        other.decrypt(encrypted)


def test_oauth_state_roundtrip() -> None:
    signer = OAuthStateSigner(STATE_SECRET)
    user_id = uuid.uuid4()

    state = signer.verify(
        signer.sign(OAuthState(user_id=user_id, provider="wahoo", platform="web")),
        provider="wahoo",
    )

    assert state == OAuthState(user_id=user_id, provider="wahoo", platform="web")


@pytest.mark.parametrize(
    ("signer", "provider"),
    [
        (OAuthStateSigner(STATE_SECRET, ttl_seconds=-1), "wahoo"),  # caducado
        (OAuthStateSigner("otro-secreto"), "wahoo"),  # firma ajena
        (OAuthStateSigner(STATE_SECRET), "strava"),  # otro proveedor
    ],
)
def test_oauth_state_rejects_invalid(signer: OAuthStateSigner, provider: str) -> None:
    token = signer.sign(OAuthState(user_id=uuid.uuid4(), provider="wahoo", platform="mobile"))

    with pytest.raises(InvalidStateError):
        OAuthStateSigner(STATE_SECRET).verify(token, provider=provider)


def test_oauth_state_rejects_garbage() -> None:
    with pytest.raises(InvalidStateError):
        OAuthStateSigner(STATE_SECRET).verify("no-es-un-state", provider="wahoo")


# --- Cliente HTTP de Wahoo ----------------------------------------------------------------


def test_authorize_url_contains_oauth_parameters() -> None:
    url = _wahoo_client(lambda _: httpx.Response(500)).authorize_url("STATE")

    assert url.startswith("https://wahoo.test/oauth/authorize?")
    assert _query(url) == {
        "client_id": "wahoo-client-id",
        "redirect_uri": "https://letismartcoach.onrender.com/auth/wahoo/callback",
        "response_type": "code",
        "scope": "user_read workouts_read workouts_write plans_read plans_write",
        "state": "STATE",
    }


def test_exchange_code_posts_form_and_parses_tokens() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _token_response()

    tokens = _wahoo_client(handler).exchange_code("CODE")

    form = parse_qs(captured[0].content.decode())
    assert captured[0].url == "https://wahoo.test/oauth/token"
    assert form["grant_type"] == ["authorization_code"]
    assert form["code"] == ["CODE"]
    assert form["client_secret"] == ["wahoo-client-secret"]
    assert tokens == WahooTokens("access-1", "refresh-1", 7200, ["user_read", "workouts_read"])


@pytest.mark.parametrize(
    "handler",
    [
        lambda _: httpx.Response(401, json={"error": "invalid_grant"}),
        lambda _: httpx.Response(200, text="no es json"),
        lambda _: httpx.Response(200, json={"sin": "token"}),
    ],
    ids=["401", "json_no_valido", "sin_access_token"],
)
def test_exchange_code_errors(handler: Handler) -> None:
    with pytest.raises(WahooAuthError):
        _wahoo_client(handler).exchange_code("CODE")


def test_network_error_is_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red", request=request)

    with pytest.raises(WahooAuthError):
        _wahoo_client(handler).refresh("refresh-1")


# --- Endpoint authorize-url (sin BD) ------------------------------------------------------


def test_authorize_url_endpoint_requires_auth(client: TestClient) -> None:
    assert client.get("/v1/integrations/wahoo/authorize-url").status_code == 401


def test_authorize_url_endpoint_signs_state_for_user(
    client: TestClient, make_token: TokenFactory
) -> None:
    response = client.get(
        "/v1/integrations/wahoo/authorize-url",
        params={"platform": "web"},
        headers={"Authorization": f"Bearer {make_token()}"},
    )

    assert response.status_code == 200
    state = _query(response.json()["authorize_url"])["state"]
    verified = OAuthStateSigner(STATE_SECRET).verify(state, provider="wahoo")
    assert verified.platform == "web"


def test_wahoo_endpoints_unavailable_without_configuration(make_token: TokenFactory) -> None:
    app = create_app(make_settings(wahoo_client_id=None))
    response = TestClient(app).get(
        "/v1/integrations/wahoo/authorize-url",
        headers={"Authorization": f"Bearer {make_token(algorithm='HS256')}"},
    )

    assert response.status_code == 503


# --- Flujo completo con BD ----------------------------------------------------------------


@pytest.fixture
def wahoo_handler() -> dict[str, Handler]:
    """Respuesta configurable del endpoint de tokens de Wahoo."""
    return {"token": lambda _: _token_response()}


@pytest.fixture
def db_app(
    engine: Engine, ec_private_key: ec.EllipticCurvePrivateKey, wahoo_handler: dict[str, Handler]
) -> FastAPI:
    settings = make_settings()
    transport = httpx.MockTransport(lambda request: wahoo_handler["token"](request))
    return create_app(
        settings,
        token_verifier=TokenVerifier(settings, FakeJWKSClient(ec_private_key.public_key())),
        database=Database(database_url_for_tests()),
        wahoo_client=WahooClient(settings, httpx.Client(transport=transport)),
    )


@pytest.fixture
def db_client(db_app: FastAPI) -> TestClient:
    return TestClient(db_app, follow_redirects=False)


def _state(user_id: uuid.UUID, platform: str = "mobile") -> str:
    return OAuthStateSigner(STATE_SECRET).sign(
        OAuthState(user_id=user_id, provider="wahoo", platform=platform)  # type: ignore[arg-type]
    )


def _integration(engine: Engine, user_id: uuid.UUID) -> Integration | None:
    with Session(engine) as session:
        return session.scalar(select(Integration).where(Integration.user_id == user_id))


@requires_db
def test_callback_saves_encrypted_tokens_and_returns_to_app(
    db_client: TestClient, engine: Engine, user_id: uuid.UUID
) -> None:
    response = db_client.get("/auth/wahoo/callback", params={"code": "C", "state": _state(user_id)})

    assert response.status_code == 302
    assert response.headers["location"] == (
        "letismartcoach://integrations?provider=wahoo&status=connected"
    )
    integration = _integration(engine, user_id)
    assert integration is not None
    assert integration.status == IntegrationStatus.ACTIVE
    assert integration.access_token_enc not in (None, "access-1")
    assert TokenCipher(FERNET_KEY).decrypt(integration.access_token_enc or "") == "access-1"
    assert integration.scopes == ["user_read", "workouts_read"]


@requires_db
@pytest.mark.parametrize(
    ("params", "reason"),
    [
        ({"error": "access_denied"}, "access_denied"),
        ({}, "authorization_failed"),
    ],
)
def test_callback_without_code_returns_error(
    db_client: TestClient, engine: Engine, user_id: uuid.UUID, params: dict[str, str], reason: str
) -> None:
    response = db_client.get("/auth/wahoo/callback", params={"state": _state(user_id), **params})

    assert _query(response.headers["location"]) == {
        "provider": "wahoo",
        "status": "error",
        "reason": reason,
    }
    assert _integration(engine, user_id) is None


@requires_db
def test_callback_with_invalid_state(db_client: TestClient) -> None:
    response = db_client.get("/auth/wahoo/callback", params={"code": "C", "state": "falso"})

    assert _query(response.headers["location"])["reason"] == "invalid_state"


@requires_db
def test_callback_token_exchange_failure(
    db_client: TestClient, user_id: uuid.UUID, wahoo_handler: dict[str, Handler]
) -> None:
    wahoo_handler["token"] = lambda _: httpx.Response(400)

    response = db_client.get("/auth/wahoo/callback", params={"code": "C", "state": _state(user_id)})

    assert _query(response.headers["location"])["reason"] == "token_exchange"


@requires_db
def test_callback_redirects_web_users_to_web_app(
    engine: Engine, ec_private_key: ec.EllipticCurvePrivateKey, user_id: uuid.UUID
) -> None:
    settings = make_settings(app_return_url_web="https://app.coachia.test/integraciones")
    app = create_app(
        settings,
        database=Database(database_url_for_tests()),
        wahoo_client=WahooClient(
            settings, httpx.Client(transport=httpx.MockTransport(lambda _: _token_response()))
        ),
    )

    response = TestClient(app, follow_redirects=False).get(
        "/auth/wahoo/callback", params={"code": "C", "state": _state(user_id, "web")}
    )

    assert response.headers["location"].startswith("https://app.coachia.test/integraciones?")


@requires_db
def test_list_and_disconnect_integrations(
    db_client: TestClient, user_id: uuid.UUID, make_token: TokenFactory, engine: Engine
) -> None:
    headers = {"Authorization": f"Bearer {make_token(sub=str(user_id))}"}
    db_client.get("/auth/wahoo/callback", params={"code": "C", "state": _state(user_id)})

    listed = db_client.get("/v1/integrations", headers=headers).json()
    assert [item["provider"] for item in listed] == ["wahoo"]
    assert "access_token_enc" not in listed[0]
    assert listed[0]["status"] == "active"

    assert db_client.delete("/v1/integrations/wahoo", headers=headers).status_code == 204
    integration = _integration(engine, user_id)
    assert integration is not None
    assert integration.status == IntegrationStatus.REVOKED
    assert integration.access_token_enc is None


@requires_db
def test_disconnect_without_integration_returns_404(
    db_client: TestClient, user_id: uuid.UUID, make_token: TokenFactory
) -> None:
    headers = {"Authorization": f"Bearer {make_token(sub=str(user_id))}"}

    assert db_client.delete("/v1/integrations/wahoo", headers=headers).status_code == 404


# --- Token válido y refresco --------------------------------------------------------------


def _connect(session: Session, user_id: uuid.UUID, expires_in: int) -> None:
    tokens = WahooTokens("access-old", "refresh-old", expires_in, ["user_read"])
    service.save_tokens(session, TokenCipher(FERNET_KEY), user_id, tokens)


@requires_db
def test_valid_token_is_returned_without_refresh(session: Session, user_id: uuid.UUID) -> None:
    _connect(session, user_id, expires_in=3600)

    def fail(_: httpx.Request) -> httpx.Response:
        raise AssertionError("No debería refrescar")

    token = service.get_valid_access_token(
        session, TokenCipher(FERNET_KEY), _wahoo_client(fail), user_id
    )

    assert token == "access-old"


@requires_db
def test_expiring_token_is_refreshed_and_saved(session: Session, user_id: uuid.UUID) -> None:
    _connect(session, user_id, expires_in=60)
    cipher = TokenCipher(FERNET_KEY)

    def handler(request: httpx.Request) -> httpx.Response:
        assert parse_qs(request.content.decode())["refresh_token"] == ["refresh-old"]
        return _token_response(access_token="access-new", refresh_token=None)

    token = service.get_valid_access_token(session, cipher, _wahoo_client(handler), user_id)

    integration = service.get_integration(session, user_id)
    assert integration is not None
    session.refresh(integration)
    assert token == "access-new"
    assert cipher.decrypt(integration.access_token_enc or "") == "access-new"
    # Wahoo no devolvió refresh token nuevo: se conserva el anterior.
    assert cipher.decrypt(integration.refresh_token_enc or "") == "refresh-old"
    assert integration.token_expires_at is not None
    assert integration.token_expires_at > datetime.now(UTC) + timedelta(hours=1)


@requires_db
def test_failed_refresh_marks_integration_as_error(session: Session, user_id: uuid.UUID) -> None:
    _connect(session, user_id, expires_in=60)

    with pytest.raises(service.WahooNotConnectedError):
        service.get_valid_access_token(
            session,
            TokenCipher(FERNET_KEY),
            _wahoo_client(lambda _: httpx.Response(401)),
            user_id,
        )

    integration = service.get_integration(session, user_id)
    assert integration is not None
    assert integration.status == IntegrationStatus.ERROR
    assert integration.last_error is not None


@requires_db
def test_valid_token_without_integration_raises(session: Session, user_id: uuid.UUID) -> None:
    with pytest.raises(service.WahooNotConnectedError):
        service.get_valid_access_token(
            session,
            TokenCipher(FERNET_KEY),
            _wahoo_client(lambda _: httpx.Response(500)),
            user_id,
        )
