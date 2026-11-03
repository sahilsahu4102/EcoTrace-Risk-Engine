"""
Retry upstream rate limits (429) and brief unavailability (503) with backoff.

Used for the three external APIs: Scrapingdog, GFW and OpenRouter. Other
failures (403 out-of-credits, 422, timeouts) are not retried: a second attempt
would fail the same way, and each service already falls back on its own.
"""

import asyncio
from collections.abc import Awaitable, Callable

import httpx

RETRY_STATUSES = frozenset({429, 503})
MAX_ATTEMPTS = 3
BASE_DELAY = 1.0  # seconds; doubles each attempt
MAX_DELAY = 8.0  # cap, including a server-sent Retry-After


def retry_delay(response: httpx.Response, attempt: int) -> float:
    """Seconds to wait before the next attempt (attempt counts from 0)."""
    retry_after = response.headers.get("Retry-After", "").strip()
    if retry_after.isdigit():
        return min(float(retry_after), MAX_DELAY)
    return min(BASE_DELAY * 2**attempt, MAX_DELAY)


async def with_retry(send: Callable[[], Awaitable[httpx.Response]]) -> httpx.Response:
    """Call `send` until it returns a non-retryable status or attempts run out."""
    for attempt in range(MAX_ATTEMPTS - 1):
        response = await send()
        if response.status_code not in RETRY_STATUSES:
            return response
        await asyncio.sleep(retry_delay(response, attempt))
    return await send()
