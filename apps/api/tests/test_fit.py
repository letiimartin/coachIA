"""Lectura de FIT sintéticos y descarga del FIT de Wahoo (sin red: transporte simulado)."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.integrations.fit import FitCorruptError, FitNoRecordsError, parse_records
from app.integrations.wahoo.client import (
    WahooApiError,
    WahooClient,
    WahooNotFoundError,
    WahooRateLimitError,
)
from tests.conftest import make_settings
from tests.fit_builder import Record, build_fit, steady_test

START = datetime(2026, 3, 1, 8, 0, tzinfo=UTC)
FIT_URL = "https://cdn.wahoo.test/files/test.fit"


def test_parse_records_reads_time_power_hr_and_cadence() -> None:
    records = parse_records(build_fit(steady_test(START, warmup_s=10, test_s=10, cooldown_s=0)))
    assert len(records) == 20
    assert records[0].timestamp == START
    assert records[-1].timestamp == START + timedelta(seconds=19)
    assert (records[0].power_w, records[0].heart_rate_bpm, records[0].cadence_rpm) == (
        150,
        135,
        90,
    )
    assert records[15].power_w == 250


def test_parse_records_keeps_missing_values_as_none_and_sorts() -> None:
    data = build_fit(
        [
            Record(START + timedelta(seconds=1), None, None, None),
            Record(START, 200, 140, 85),
            Record(START + timedelta(seconds=1), 210, None, None),  # repetido: gana el último
        ]
    )
    records = parse_records(data)
    assert [r.timestamp for r in records] == [START, START + timedelta(seconds=1)]
    assert records[1].power_w == 210
    assert records[1].heart_rate_bpm is None and records[1].cadence_rpm is None


def test_corrupt_file_fails_with_clear_error() -> None:
    data = bytearray(build_fit(steady_test(START, warmup_s=10, test_s=10, cooldown_s=0)))
    data[40] ^= 0xFF  # rompe el CRC
    with pytest.raises(FitCorruptError):
        parse_records(bytes(data))
    with pytest.raises(FitCorruptError):
        parse_records(b"esto no es un FIT")
    with pytest.raises(FitCorruptError):
        parse_records(build_fit(steady_test(START))[:-200])


def test_file_without_records_fails() -> None:
    with pytest.raises(FitNoRecordsError):
        parse_records(build_fit([]))


# --- Descarga del FIT ------------------------------------------------------------------------


def _client(handler: httpx.MockTransport) -> WahooClient:
    return WahooClient(make_settings(), httpx.Client(transport=handler))


def test_download_fit_does_not_send_the_wahoo_token() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, content=b"fit-bytes")

    assert _client(httpx.MockTransport(handler)).download_fit(FIT_URL) == b"fit-bytes"
    assert str(captured[0].url) == FIT_URL
    assert "authorization" not in captured[0].headers


@pytest.mark.parametrize("url", ["http://cdn.wahoo.test/a.fit", "file:///etc/passwd", "nada"])
def test_download_fit_requires_https(url: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - no se llama
        raise AssertionError("no debe descargar")

    with pytest.raises(WahooApiError):
        _client(httpx.MockTransport(handler)).download_fit(url)


@pytest.mark.parametrize(
    ("status", "error"),
    [(404, WahooNotFoundError), (429, WahooRateLimitError), (500, WahooApiError)],
)
def test_download_fit_errors(status: int, error: type[Exception]) -> None:
    client = _client(httpx.MockTransport(lambda request: httpx.Response(status)))
    with pytest.raises(error):
        client.download_fit(FIT_URL)


def test_download_fit_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red")

    with pytest.raises(WahooApiError):
        _client(httpx.MockTransport(handler)).download_fit(FIT_URL)
