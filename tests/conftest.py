import httpx
import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail any test that reaches the real network. Local runs load real keys from .env."""
    attempts = []

    async def blocked_send(self, request, *args, **kwargs):
        attempts.append(str(request.url))
        raise httpx.ConnectError("network disabled in tests", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", blocked_send)
    yield
    assert not attempts, f"unexpected network call(s): {attempts}"


@pytest.fixture
def cache_db_path(tmp_path, monkeypatch):
    from app.services import cache_db

    path = str(tmp_path / "risk_cache.db")
    monkeypatch.setattr(cache_db, "DB_PATH", path)
    cache_db.init_db()
    return path
