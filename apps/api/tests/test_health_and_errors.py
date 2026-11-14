from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import __version__
from app.db.session import Database
from app.main import create_app
from tests.conftest import FERNET_KEY, make_settings


def test_root_describes_the_api(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"name": "CoachIA API", "version": __version__, "health": "/health"}


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_readiness_without_database_is_ok_but_reports_it(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "not_configured"}}


def test_readiness_with_reachable_database() -> None:
    app = create_app(make_settings(), database=Database("sqlite://"))

    response = TestClient(app).get("/health/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["database"] == "ok"


def test_readiness_with_unreachable_database_returns_503() -> None:
    database = Database("sqlite:////ruta/que/no/existe/coachia.db")
    app = create_app(make_settings(), database=database)

    response = TestClient(app).get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "checks": {"database": "error"}}


def test_request_id_is_generated_and_propagated(client: TestClient) -> None:
    generated = client.get("/health").headers["X-Request-ID"]
    propagated = client.get("/health", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"]
    sanitized = client.get("/health", headers={"X-Request-ID": "<script>"}).headers["X-Request-ID"]

    assert len(generated) == 32
    assert propagated == "abc-123"
    assert sanitized != "<script>"


def test_unknown_route_uses_error_format(client: TestClient) -> None:
    response = client.get("/no-existe")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_unhandled_exception_does_not_leak_details(app: FastAPI) -> None:
    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("detalle interno secreto")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "internal_error",
        "message": "Error interno del servidor.",
    }
    assert "secreto" not in response.text


def test_docs_are_disabled_in_production() -> None:
    settings = make_settings(
        environment="production",
        database_url="postgresql://u:p@localhost:5432/db",
        token_encryption_key=FERNET_KEY,
        oauth_state_secret="state-secret",
    )
    app = create_app(settings, database=Database(None))

    assert TestClient(app).get("/docs").status_code == 404
