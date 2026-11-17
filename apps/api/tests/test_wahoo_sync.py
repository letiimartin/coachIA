import copy
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.core.crypto import TokenCipher
from app.core.security import TokenVerifier
from app.db.session import Database
from app.integrations.wahoo import service, sync
from app.integrations.wahoo.client import (
    WahooApiError,
    WahooClient,
    WahooNotFoundError,
    WahooRateLimitError,
    WahooTokens,
    WahooUnauthorizedError,
)
from app.main import create_app
from app.models import Activity, Integration, IntegrationStatus
from tests.conftest import (
    FERNET_KEY,
    INTERNAL_KEY,
    FakeJWKSClient,
    TokenFactory,
    database_url_for_tests,
    make_settings,
    requires_db,
)
from tests.test_wahoo_mapper import load_fixture

Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler) -> WahooClient:
    return WahooClient(make_settings(), httpx.Client(transport=httpx.MockTransport(handler)))


# --- Cliente: listado y resumen -----------------------------------------------------------


def test_list_workouts_sends_token_and_pagination() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=load_fixture("workouts_page_1.json"))

    page = _client(handler).list_workouts("tok", page=3, per_page=2)

    request = captured[0]
    assert request.url.path == "/v1/workouts"
    assert dict(request.url.params) == {"page": "3", "per_page": "2"}
    assert request.headers["Authorization"] == "Bearer tok"
    assert (page.total, page.page, page.per_page) == (3, 1, 2)
    assert [w["id"] for w in page.workouts] == [56600, 56519]


def test_get_workout_summary() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/workouts/56400/workout_summary"
        return httpx.Response(200, json=load_fixture("workout_summary.json"))

    assert _client(handler).get_workout_summary("tok", 56400)["id"] == 8200


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(401), WahooUnauthorizedError),
        (httpx.Response(403), WahooUnauthorizedError),
        (httpx.Response(404), WahooNotFoundError),
        (httpx.Response(429, headers={"X-RateLimit-Reset": "300"}), WahooRateLimitError),
        (httpx.Response(500), WahooApiError),
        (httpx.Response(200, text="no es json"), WahooApiError),
        (httpx.Response(200, json={"sin": "workouts"}), WahooApiError),
    ],
    ids=["401", "403", "404", "429", "500", "no_json", "sin_workouts"],
)
def test_list_workouts_errors(response: httpx.Response, error: type[Exception]) -> None:
    with pytest.raises(error):
        _client(lambda _: response).list_workouts("tok")


def test_rate_limit_error_carries_reset_seconds() -> None:
    response = httpx.Response(429, headers={"X-RateLimit-Reset": "300"})

    with pytest.raises(WahooRateLimitError) as info:
        _client(lambda _: response).list_workouts("tok")

    assert info.value.retry_after == 300


def test_network_error_on_api_call_is_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("lento", request=request)

    with pytest.raises(WahooApiError):
        _client(handler).get_workout_summary("tok", 1)


# --- Sincronización con BD ----------------------------------------------------------------


class FakeWahoo:
    """Wahoo simulado: listado paginado según las fixtures y resúmenes por id."""

    def __init__(self) -> None:
        self.pages = {
            1: load_fixture("workouts_page_1.json"),
            2: load_fixture("workouts_page_2.json"),
        }
        self.summaries = {"56400": load_fixture("workout_summary.json")}
        self.requests: list[httpx.Request] = []
        self.override: Handler | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.override is not None:
            return self.override(request)
        path = request.url.path
        if path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "new", "expires_in": 7200})
        if path == "/v1/workouts":
            page = int(request.url.params.get("page", "1"))
            empty = {"workouts": [], "total": 3, "page": page, "per_page": 2}
            return httpx.Response(200, json=self.pages.get(page, empty))
        if path.endswith("/workout_summary"):
            summary = self.summaries.get(path.split("/")[3])
            return httpx.Response(200, json=summary) if summary else httpx.Response(404)
        return httpx.Response(404)

    def paths(self) -> list[str]:
        return [
            r.url.path + (f"?page={r.url.params['page']}" if "page" in r.url.params else "")
            for r in self.requests
        ]


@pytest.fixture
def fake_wahoo() -> FakeWahoo:
    return FakeWahoo()


@pytest.fixture
def wahoo(fake_wahoo: FakeWahoo) -> WahooClient:
    return _client(fake_wahoo)


@pytest.fixture
def cipher() -> TokenCipher:
    return TokenCipher(FERNET_KEY)


def _connect(session: Session, user_id: uuid.UUID) -> None:
    tokens = WahooTokens("access-1", "refresh-1", 3600, ["workouts_read"])
    service.save_tokens(session, TokenCipher(FERNET_KEY), user_id, tokens)


def _activities(engine: Engine, user_id: uuid.UUID) -> list[Activity]:
    with Session(engine) as session:
        return list(
            session.scalars(
                select(Activity).where(Activity.user_id == user_id).order_by(Activity.start_at)
            )
        )


def _integration(engine: Engine, user_id: uuid.UUID) -> Integration:
    with Session(engine) as session:
        integration = session.scalar(select(Integration).where(Integration.user_id == user_id))
        assert integration is not None
        return integration


@requires_db
def test_first_sync_imports_completed_workouts(
    session: Session,
    engine: Engine,
    user_id: uuid.UUID,
    wahoo: WahooClient,
    cipher: TokenCipher,
    fake_wahoo: FakeWahoo,
) -> None:
    _connect(session, user_id)

    result = sync.sync_user(session, cipher, wahoo, user_id)

    assert (result.created, result.updated, result.unchanged) == (2, 0, 0)
    activities = _activities(engine, user_id)
    assert [(a.external_id, a.sport, a.source) for a in activities] == [
        ("56400", "trail_running", "wahoo"),
        ("56519", "cycling", "wahoo"),
    ]
    ride = activities[1]
    assert ride.elapsed_s == 275
    assert ride.raw["workout_summary"]["id"] == 8297
    assert (ride.load, ride.load_method, ride.intensity_factor) == (None, None, None)
    # El planificado (sin resumen) no se importa; el resumen del 56400 se pide aparte.
    assert fake_wahoo.paths() == [
        "/v1/workouts?page=1",
        "/v1/workouts?page=2",
        "/v1/workouts/56400/workout_summary",
    ]
    integration = _integration(engine, user_id)
    assert integration.last_sync_at is not None
    assert integration.last_error is None
    assert integration.sync_cursor == {"latest_start_at": "2015-08-12T09:00:00+00:00"}


@requires_db
def test_repeated_sync_is_idempotent_and_detects_changes(
    session: Session,
    engine: Engine,
    user_id: uuid.UUID,
    wahoo: WahooClient,
    cipher: TokenCipher,
    fake_wahoo: FakeWahoo,
) -> None:
    _connect(session, user_id)
    sync.sync_user(session, cipher, wahoo, user_id)
    first_ids = {a.external_id: a.id for a in _activities(engine, user_id)}

    # El segundo sync es incremental: el workout de 2015-08-01 queda fuera del margen.
    again = sync.sync_user(session, cipher, wahoo, user_id)
    assert (again.created, again.updated, again.unchanged) == (0, 0, 1)

    edited = copy.deepcopy(fake_wahoo.pages[1])
    edited["workouts"][1]["workout_summary"]["heart_rate_avg"] = "101.00"
    fake_wahoo.pages[1] = edited
    changed = sync.sync_user(session, cipher, wahoo, user_id)

    assert (changed.created, changed.updated, changed.unchanged) == (0, 1, 0)
    activities = _activities(engine, user_id)
    assert {a.external_id: a.id for a in activities} == first_ids
    assert activities[1].avg_hr == 101


@requires_db
def test_incremental_sync_stops_at_known_workouts(
    session: Session,
    engine: Engine,
    user_id: uuid.UUID,
    wahoo: WahooClient,
    cipher: TokenCipher,
    fake_wahoo: FakeWahoo,
) -> None:
    _connect(session, user_id)
    integration = service.get_integration(session, user_id)
    assert integration is not None
    # Último inicio conocido: 2015-08-12. El de 2015-08-01 queda fuera del margen de 7 días.
    integration.sync_cursor = {"latest_start_at": "2015-08-12T09:00:00+00:00"}
    session.commit()

    result = sync.sync_user(session, cipher, wahoo, user_id)

    assert (result.created, result.updated) == (1, 0)
    assert fake_wahoo.paths() == ["/v1/workouts?page=1", "/v1/workouts?page=2"]
    assert [a.external_id for a in _activities(engine, user_id)] == ["56519"]


@requires_db
def test_unauthorized_marks_integration_as_error(
    session: Session,
    engine: Engine,
    user_id: uuid.UUID,
    wahoo: WahooClient,
    cipher: TokenCipher,
    fake_wahoo: FakeWahoo,
) -> None:
    _connect(session, user_id)
    fake_wahoo.override = lambda _: httpx.Response(401)

    with pytest.raises(WahooUnauthorizedError):
        sync.sync_user(session, cipher, wahoo, user_id)

    integration = _integration(engine, user_id)
    assert integration.status == IntegrationStatus.ERROR
    assert integration.last_error is not None
    assert integration.last_sync_at is None


@requires_db
def test_transient_error_keeps_integration_active_and_imported_pages(
    session: Session,
    engine: Engine,
    user_id: uuid.UUID,
    wahoo: WahooClient,
    cipher: TokenCipher,
    fake_wahoo: FakeWahoo,
) -> None:
    _connect(session, user_id)
    normal = FakeWahoo()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("page") == "2":
            return httpx.Response(429, headers={"X-RateLimit-Reset": "120"})
        return normal(request)

    fake_wahoo.override = handler

    with pytest.raises(WahooRateLimitError):
        sync.sync_user(session, cipher, wahoo, user_id)

    integration = _integration(engine, user_id)
    assert integration.status == IntegrationStatus.ACTIVE
    assert integration.last_error is not None
    assert integration.sync_cursor == {}  # El cursor no avanza si el sync no termina.
    assert [a.external_id for a in _activities(engine, user_id)] == ["56519"]


@requires_db
def test_sync_without_integration_raises(
    session: Session, user_id: uuid.UUID, wahoo: WahooClient, cipher: TokenCipher
) -> None:
    with pytest.raises(service.WahooNotConnectedError):
        sync.sync_user(session, cipher, wahoo, user_id)


# --- Endpoints ----------------------------------------------------------------------------


@pytest.fixture
def db_app(
    engine: Engine, ec_private_key: ec.EllipticCurvePrivateKey, fake_wahoo: FakeWahoo
) -> FastAPI:
    settings = make_settings()
    return create_app(
        settings,
        token_verifier=TokenVerifier(settings, FakeJWKSClient(ec_private_key.public_key())),
        database=Database(database_url_for_tests()),
        wahoo_client=_client(fake_wahoo),
    )


@pytest.fixture
def api(db_app: FastAPI) -> TestClient:
    return TestClient(db_app)


def _auth(make_token: TokenFactory, user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(sub=str(user_id))}"}


@requires_db
def test_sync_endpoint_returns_counts(
    api: TestClient, session: Session, user_id: uuid.UUID, make_token: TokenFactory
) -> None:
    _connect(session, user_id)
    headers = _auth(make_token, user_id)

    first = api.post("/v1/integrations/wahoo/sync", headers=headers)
    second = api.post("/v1/integrations/wahoo/sync", headers=headers)

    assert first.status_code == 200
    assert first.json() == {"created": 2, "updated": 0, "unchanged": 0}
    assert second.json() == {"created": 0, "updated": 0, "unchanged": 1}


@requires_db
def test_sync_endpoint_requires_auth(api: TestClient) -> None:
    assert api.post("/v1/integrations/wahoo/sync").status_code == 401


@requires_db
def test_sync_endpoint_without_wahoo_returns_conflict(
    api: TestClient, user_id: uuid.UUID, make_token: TokenFactory
) -> None:
    response = api.post("/v1/integrations/wahoo/sync", headers=_auth(make_token, user_id))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


@requires_db
@pytest.mark.parametrize(
    ("wahoo_response", "status", "code"),
    [
        (httpx.Response(401), 409, "conflict"),
        (httpx.Response(429, headers={"X-RateLimit-Reset": "300"}), 429, "too_many_requests"),
        (httpx.Response(503), 502, "bad_gateway"),
    ],
    ids=["401", "429", "503"],
)
def test_sync_endpoint_maps_wahoo_errors(
    api: TestClient,
    session: Session,
    user_id: uuid.UUID,
    make_token: TokenFactory,
    fake_wahoo: FakeWahoo,
    wahoo_response: httpx.Response,
    status: int,
    code: str,
) -> None:
    _connect(session, user_id)
    fake_wahoo.override = lambda _: wahoo_response

    response = api.post("/v1/integrations/wahoo/sync", headers=_auth(make_token, user_id))

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    if status == 429:
        assert response.headers["Retry-After"] == "300"


@requires_db
def test_internal_sync_requires_key(api: TestClient) -> None:
    assert api.post("/internal/sync/wahoo").status_code == 401


@requires_db
def test_internal_sync_processes_active_integrations(
    api: TestClient, session: Session, engine: Engine, user_id: uuid.UUID
) -> None:
    # Limpia integraciones de otros tests para contar sólo las de este.
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM integrations"))
    _connect(session, user_id)
    other_id = uuid.uuid4()
    revoked_id = uuid.uuid4()
    with engine.begin() as conn:
        for new_id in (other_id, revoked_id):
            conn.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": new_id})
    try:
        _connect(session, other_id)
        _connect(session, revoked_id)
        service.disconnect(session, revoked_id)

        response = api.post("/internal/sync/wahoo", headers={"X-Internal-API-Key": INTERNAL_KEY})

        assert response.status_code == 200
        assert response.json() == {
            "integrations": 2,
            "succeeded": 2,
            "failed": 0,
            "rate_limited": False,
            "created": 4,
            "updated": 0,
            "unchanged": 0,
        }
        assert _integration(engine, other_id).last_sync_at is not None
    finally:
        session.rollback()
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM auth.users WHERE id IN (:a, :b)"),
                {"a": other_id, "b": revoked_id},
            )


@requires_db
def test_internal_sync_stops_on_rate_limit_and_continues_on_user_errors(
    session: Session,
    engine: Engine,
    user_id: uuid.UUID,
    wahoo: WahooClient,
    cipher: TokenCipher,
    fake_wahoo: FakeWahoo,
) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM integrations"))
    _connect(session, user_id)
    fake_wahoo.override = lambda _: httpx.Response(500)

    failed = sync.sync_all(session, cipher, wahoo)
    assert (failed.integrations, failed.succeeded, failed.failed) == (1, 0, 1)
    assert not failed.rate_limited

    fake_wahoo.override = lambda _: httpx.Response(429)
    limited = sync.sync_all(session, cipher, wahoo)
    assert limited.rate_limited
    assert _integration(engine, user_id).status == IntegrationStatus.ACTIVE


def test_cursor_parsing_ignores_garbage() -> None:
    assert sync._parse_cursor({"latest_start_at": "no"}) is None
    assert sync._parse_cursor(None) is None
    assert sync._parse_cursor({"latest_start_at": "2015-08-12T09:00:00+00:00"}) == datetime(
        2015, 8, 12, 9, tzinfo=UTC
    )
