import copy
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
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
from app.models import (
    Activity,
    AthleteThreshold,
    DailyLoad,
    Integration,
    IntegrationStatus,
    LoadMethod,
)
from app.services import fitness
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

# Las fixtures de Wahoo son de agosto de 2015: los tests de sync fijan «ahora» poco después para
# que la ventana de la primera importación (#63) las incluya.
NOW = datetime(2015, 9, 1, tzinfo=UTC)
DAYS = 183


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "_now", lambda: NOW)


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

    result = sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=DAYS)

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
    sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=DAYS)
    first_ids = {a.external_id: a.id for a in _activities(engine, user_id)}

    # El segundo sync es incremental: el workout de 2015-08-01 queda fuera del margen.
    again = sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=DAYS)
    assert (again.created, again.updated, again.unchanged) == (0, 0, 1)

    edited = copy.deepcopy(fake_wahoo.pages[1])
    edited["workouts"][1]["workout_summary"]["heart_rate_avg"] = "101.00"
    fake_wahoo.pages[1] = edited
    changed = sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=DAYS)

    assert (changed.created, changed.updated, changed.unchanged) == (0, 1, 0)
    activities = _activities(engine, user_id)
    assert {a.external_id: a.id for a in activities} == first_ids
    assert activities[1].avg_hr == 101


@requires_db
def test_sync_computes_load_and_recomputes_the_series(
    session: Session,
    engine: Engine,
    user_id: uuid.UUID,
    wahoo: WahooClient,
    cipher: TokenCipher,
    fake_wahoo: FakeWahoo,
) -> None:
    _connect(session, user_id)
    session.add(AthleteThreshold(user_id=user_id, effective_from=date(2015, 1, 1), ftp_w=200))
    session.commit()

    sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=DAYS)

    ride = _activities(engine, user_id)[1]
    # 179 s en movimiento a NP 150 con FTP 200: IF 0.75 -> 179/3600 · 0.5625 · 100 = 2.8.
    assert (ride.load, ride.load_method, ride.intensity_factor) == (
        Decimal("2.8"),
        LoadMethod.POWER,
        Decimal("0.750"),
    )
    assert _daily_load(engine, user_id, date(2015, 8, 12)) == Decimal("2.8")

    # Un sync que modifica una actividad que ya tiene carga no la cambia (protección de #22):
    # eso sólo lo hace el recálculo histórico explícito.
    edited = copy.deepcopy(fake_wahoo.pages[1])
    edited["workouts"][1]["workout_summary"]["power_bike_np_last"] = "200.00"
    fake_wahoo.pages[1] = edited
    sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=DAYS)

    assert _activities(engine, user_id)[1].load == Decimal("2.8")
    assert _daily_load(engine, user_id, date(2015, 8, 12)) == Decimal("2.8")

    fitness.recompute_from(session, user_id, date(2015, 8, 12), overwrite_existing=True)
    session.commit()
    assert _activities(engine, user_id)[1].load == Decimal("5.0")
    assert _daily_load(engine, user_id, date(2015, 8, 12)) == Decimal("5.0")


def _daily_load(engine: Engine, user_id: uuid.UUID, day: date) -> Decimal | None:
    with Session(engine) as session:
        return session.scalar(
            select(DailyLoad.load).where(DailyLoad.user_id == user_id, DailyLoad.day == day)
        )


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

    # Con cursor, la ventana de la primera importación no se aplica (aunque sea de 1 día).
    result = sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=1)

    assert (result.created, result.updated) == (1, 0)
    assert fake_wahoo.paths() == ["/v1/workouts?page=1", "/v1/workouts?page=2"]
    assert [a.external_id for a in _activities(engine, user_id)] == ["56519"]


@requires_db
def test_first_sync_only_imports_the_initial_window(
    session: Session,
    engine: Engine,
    user_id: uuid.UUID,
    wahoo: WahooClient,
    cipher: TokenCipher,
    fake_wahoo: FakeWahoo,
) -> None:
    _connect(session, user_id)

    # Ventana de 20 días desde el 2015-09-01: entra el del 2015-08-12, no el del 2015-08-01.
    result = sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=20)

    assert (result.created, result.updated, result.unchanged) == (1, 0, 0)
    assert [a.external_id for a in _activities(engine, user_id)] == ["56519"]
    # Para al encontrar el primer workout anterior a la ventana: no pide su resumen.
    assert fake_wahoo.paths() == ["/v1/workouts?page=1", "/v1/workouts?page=2"]
    assert _integration(engine, user_id).sync_cursor == {
        "latest_start_at": "2015-08-12T09:00:00+00:00"
    }


@requires_db
def test_first_sync_outside_the_window_imports_nothing(
    session: Session,
    engine: Engine,
    user_id: uuid.UUID,
    wahoo: WahooClient,
    cipher: TokenCipher,
    fake_wahoo: FakeWahoo,
) -> None:
    _connect(session, user_id)

    result = sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=1)

    assert (result.created, result.updated, result.unchanged) == (0, 0, 0)
    assert _activities(engine, user_id) == []
    assert fake_wahoo.paths() == ["/v1/workouts?page=1"]
    integration = _integration(engine, user_id)
    # Sin nada importado no hay cursor: la siguiente sync vuelve a ser la primera.
    assert integration.sync_cursor == {}
    assert integration.last_sync_at == NOW


@requires_db
def test_window_does_not_delete_activities_already_imported(
    session: Session,
    engine: Engine,
    user_id: uuid.UUID,
    wahoo: WahooClient,
    cipher: TokenCipher,
) -> None:
    _connect(session, user_id)
    sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=DAYS)
    integration = service.get_integration(session, user_id)
    assert integration is not None
    integration.sync_cursor = {}  # Como si fuera otra vez la primera, con una ventana corta.
    session.commit()

    sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=1)

    assert [a.external_id for a in _activities(engine, user_id)] == ["56400", "56519"]


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
        sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=DAYS)

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
        sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=DAYS)

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
        sync.sync_user(session, cipher, wahoo, user_id, initial_sync_days=DAYS)


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
def test_sync_endpoints_use_the_configured_window(
    engine: Engine,
    ec_private_key: ec.EllipticCurvePrivateKey,
    fake_wahoo: FakeWahoo,
    session: Session,
    user_id: uuid.UUID,
    make_token: TokenFactory,
) -> None:
    settings = make_settings(wahoo_initial_sync_days=20)
    api = TestClient(
        create_app(
            settings,
            token_verifier=TokenVerifier(settings, FakeJWKSClient(ec_private_key.public_key())),
            database=Database(database_url_for_tests()),
            wahoo_client=_client(fake_wahoo),
        )
    )
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM integrations"))
    _connect(session, user_id)

    manual = api.post("/v1/integrations/wahoo/sync", headers=_auth(make_token, user_id))
    assert manual.json() == {"created": 1, "updated": 0, "unchanged": 0}

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM activities WHERE user_id = :id"), {"id": user_id})
        conn.execute(
            text("UPDATE integrations SET sync_cursor = '{}'::jsonb WHERE user_id = :id"),
            {"id": user_id},
        )
    automatic = api.post("/internal/sync/wahoo", headers={"X-Internal-API-Key": INTERNAL_KEY})
    assert automatic.json()["created"] == 1


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

    failed = sync.sync_all(session, cipher, wahoo, initial_sync_days=DAYS)
    assert (failed.integrations, failed.succeeded, failed.failed) == (1, 0, 1)
    assert not failed.rate_limited

    fake_wahoo.override = lambda _: httpx.Response(429)
    limited = sync.sync_all(session, cipher, wahoo, initial_sync_days=DAYS)
    assert limited.rate_limited
    assert _integration(engine, user_id).status == IntegrationStatus.ACTIVE


def test_initial_sync_days_defaults_to_six_months_and_is_configurable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WAHOO_INITIAL_SYNC_DAYS", raising=False)
    assert Settings(_env_file=None).wahoo_initial_sync_days == 183  # type: ignore[call-arg]
    monkeypatch.setenv("WAHOO_INITIAL_SYNC_DAYS", "30")
    assert Settings(_env_file=None).wahoo_initial_sync_days == 30  # type: ignore[call-arg]
    monkeypatch.setenv("WAHOO_INITIAL_SYNC_DAYS", "0")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_cursor_parsing_ignores_garbage() -> None:
    assert sync._parse_cursor({"latest_start_at": "no"}) is None
    assert sync._parse_cursor(None) is None
    assert sync._parse_cursor({"latest_start_at": "2015-08-12T09:00:00+00:00"}) == datetime(
        2015, 8, 12, 9, tzinfo=UTC
    )
