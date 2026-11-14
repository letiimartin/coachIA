from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import INTERNAL_KEY, STRAVA_TOKEN, make_settings


class TestInternalApi:
    def test_ping_with_valid_key(self, client: TestClient) -> None:
        response = client.get("/internal/ping", headers={"X-Internal-API-Key": INTERNAL_KEY})

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.parametrize("headers", [{}, {"X-Internal-API-Key": "incorrecta"}])
    def test_ping_rejects_missing_or_wrong_key(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        response = client.get("/internal/ping", headers=headers)

        assert response.status_code == 401

    def test_ping_is_disabled_without_configured_key(self) -> None:
        client = TestClient(create_app(make_settings(internal_api_key=None)))

        response = client.get("/internal/ping", headers={"X-Internal-API-Key": "lo-que-sea"})

        assert response.status_code == 403


class TestStravaWebhook:
    def _verify(self, client: TestClient, **params: str) -> Any:
        query = {"hub.mode": "subscribe", "hub.verify_token": STRAVA_TOKEN, "hub.challenge": "xyz"}
        query.update(params)
        return client.get("/webhooks/strava", params=query)

    def test_subscription_verification_returns_challenge(self, client: TestClient) -> None:
        response = self._verify(client)

        assert response.status_code == 200
        assert response.json() == {"hub.challenge": "xyz"}

    def test_subscription_with_wrong_token_is_forbidden(self, client: TestClient) -> None:
        assert self._verify(client, **{"hub.verify_token": "malo"}).status_code == 403

    def test_subscription_with_wrong_mode_is_forbidden(self, client: TestClient) -> None:
        assert self._verify(client, **{"hub.mode": "unsubscribe"}).status_code == 403

    def test_subscription_without_configured_token_is_forbidden(self) -> None:
        client = TestClient(create_app(make_settings(strava_verify_token=None)))

        assert self._verify(client).status_code == 403

    def test_event_is_accepted(self, client: TestClient) -> None:
        event = {
            "object_type": "activity",
            "object_id": 123,
            "aspect_type": "create",
            "owner_id": 456,
            "subscription_id": 789,
            "event_time": 1_731_600_000,
        }

        response = client.post("/webhooks/strava", json=event)

        assert response.status_code == 200
        assert response.json() == {"received": True}

    def test_invalid_event_returns_validation_error(self, client: TestClient) -> None:
        response = client.post("/webhooks/strava", json={"object_type": "otro"})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
