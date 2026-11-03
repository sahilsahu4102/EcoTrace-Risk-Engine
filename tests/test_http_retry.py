import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from app.services import http_retry
from app.services.http_retry import MAX_ATTEMPTS, retry_delay, with_retry


@pytest.fixture
def real_delays(monkeypatch):
    monkeypatch.setattr(http_retry, "BASE_DELAY", 1.0)
    monkeypatch.setattr(http_retry, "MAX_DELAY", 8.0)


def test_backoff_doubles_and_is_capped(real_delays):
    limited = httpx.Response(429)
    assert [retry_delay(limited, n) for n in range(5)] == [1.0, 2.0, 4.0, 8.0, 8.0]


def test_retry_after_header_wins_but_is_capped(real_delays):
    assert retry_delay(httpx.Response(429, headers={"Retry-After": "3"}), 0) == 3.0
    assert retry_delay(httpx.Response(429, headers={"Retry-After": "120"}), 0) == 8.0
    # an HTTP-date Retry-After is not parsed; plain backoff applies
    assert retry_delay(httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}), 1) == 2.0


@pytest.mark.parametrize("status", [200, 403, 404, 422, 500])
def test_non_retryable_status_returns_after_one_call(status):
    send = AsyncMock(return_value=httpx.Response(status))
    assert asyncio.run(with_retry(send)).status_code == status
    assert send.await_count == 1


def test_gives_up_after_max_attempts_with_the_last_response():
    send = AsyncMock(return_value=httpx.Response(503))
    assert asyncio.run(with_retry(send)).status_code == 503
    assert send.await_count == MAX_ATTEMPTS


def test_recovers_when_the_limit_clears():
    send = AsyncMock(side_effect=[httpx.Response(429), httpx.Response(429), httpx.Response(200)])
    assert asyncio.run(with_retry(send)).status_code == 200
