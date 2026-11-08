import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from app.services import extraction
from app.services.extraction import (
    get_commodity_by_name,
    is_commodity_query,
    extract_entities,
)


def _names(items):
    return sorted(i["name"] for i in items)


def _llm_reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


@pytest.fixture
def no_llm_key(monkeypatch):
    monkeypatch.setattr(extraction, "OPENROUTER_API_KEY", "")


@pytest.fixture
def llm(monkeypatch):
    """Configured key plus a mocked OpenRouter POST; set .return_value or .side_effect per test."""
    monkeypatch.setattr(extraction, "OPENROUTER_API_KEY", "test-key")
    post = AsyncMock()
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    return post


def test_get_commodity_by_name():
    commodity = get_commodity_by_name("Palm Oil")
    assert commodity is not None
    assert commodity.name == "Palm Oil"
    assert get_commodity_by_name("pAlM oIl") is not None
    assert get_commodity_by_name("Nonexistent Commodity") is None


def test_is_commodity_query():
    assert is_commodity_query("Palm Oil") is True
    assert is_commodity_query("Soybean") is True  # matches keyword
    assert is_commodity_query("apple") is False


def test_extract_entities_empty():
    res = asyncio.run(extract_entities(""))
    assert res.commodities == []
    assert res.regions == []
    assert res.operational_regions == []


def test_keyword_fallback_without_api_key(no_llm_key):
    res = asyncio.run(extract_entities("We source soy from Brazil and palm oil from Indonesia."))

    assert {"Soy", "Palm Oil"} <= set(_names(res.commodities))
    assert {"BRA", "IDN"} <= {r["iso_code"] for r in res.regions}
    assert all(r["sourcing_confidence"] == "inferred" for r in res.regions)
    assert res.operational_regions == []


def test_llm_output_is_mapped_to_allowed_lists(llm):
    llm.return_value = _llm_reply(
        '```json\n{"commodities": ["cocoa", "Unobtainium", "Cocoa"], '
        '"sourcing_countries": ["Ivory Coast", "Ghana", "Atlantis"], '
        '"operational_countries": ["China"]}\n```'
    )

    res = asyncio.run(extract_entities("Some CSR text about cocoa."))

    assert _names(res.commodities) == ["Cocoa"]  # case-insensitive, unknown dropped, deduplicated
    assert _names(res.regions) == ["Côte d'Ivoire", "Ghana"]  # alias resolved, unknown dropped
    assert all(r["sourcing_confidence"] == "estimated" for r in res.regions)
    assert _names(res.operational_regions) == ["China"]
    assert res.operational_regions[0]["sourcing_confidence"] == "operational_only"


def test_llm_prompt_caps_text_at_40k_chars(llm):
    llm.return_value = _llm_reply('{"commodities": [], "sourcing_countries": [], "operational_countries": []}')

    asyncio.run(extract_entities("#" * 50_000))

    payload = llm.call_args.kwargs["json"]
    assert payload["temperature"] == 0.0
    assert payload["messages"][1]["content"].count("#") == 40_000


@pytest.mark.parametrize(
    "reply",
    [
        _llm_reply("this is not json"),
        httpx.Response(429, text="Too Many Requests"),
        httpx.Response(500, text="upstream error"),
    ],
    ids=["invalid-json", "rate-limited", "server-error"],
)
def test_llm_failure_falls_back_to_keywords(llm, reply):
    llm.return_value = reply

    res = asyncio.run(extract_entities("We buy cocoa from Ghana."))

    assert _names(res.commodities) == ["Cocoa"]
    assert _names(res.regions) == ["Ghana"]
    assert res.regions[0]["evidence_source"].startswith("Keyword matching")


def test_llm_timeout_falls_back_to_keywords(llm):
    llm.side_effect = httpx.ReadTimeout("timed out")

    res = asyncio.run(extract_entities("We buy cocoa from Ghana."))

    assert _names(res.commodities) == ["Cocoa"]
    assert llm.await_count == 1  # no retry


def test_unavailable_models_are_skipped_until_one_answers(monkeypatch):
    """A 402 (no credits) or 404 (model withdrawn) moves on to the next free model."""
    monkeypatch.setattr(extraction, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(extraction, "OPENROUTER_MODEL", "paid/model")
    monkeypatch.setattr(extraction, "FREE_MODELS", ["gone/model:free", "working/model:free"])
    answers = {
        "paid/model": httpx.Response(402, text="Insufficient credits"),
        "gone/model:free": httpx.Response(404, text="unavailable"),
        "working/model:free": httpx.Response(200, json={"choices": [{"message": {"content":
            '{"commodities": ["Cocoa"], "sourcing_countries": ["Ghana"], "operational_countries": []}'}}]}),
    }
    tried = []

    async def post(self, url, json=None, **kwargs):
        tried.append(json["model"])
        return answers[json["model"]]

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    res = asyncio.run(extraction.extract_entities("We source cocoa from Ghana. " * 5))

    assert tried == ["paid/model", "gone/model:free", "working/model:free"]
    assert [c["name"] for c in res.commodities] == ["Cocoa"]
    assert [r["name"] for r in res.regions] == ["Ghana"]


def test_json_wrapped_in_prose_is_still_parsed(monkeypatch):
    monkeypatch.setattr(extraction, "OPENROUTER_API_KEY", "test-key")
    reply = 'Sure! Here it is: {"commodities": ["Soy"], "sourcing_countries": ["Brazil"], "operational_countries": []} Done.'

    async def post(self, url, json=None, **kwargs):
        return httpx.Response(200, json={"choices": [{"message": {"content": reply}}]})

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    res = asyncio.run(extraction.extract_entities("We buy soy from Brazil. " * 5))
    assert [c["name"] for c in res.commodities] == ["Soy"]
    assert [r["sourcing_confidence"] for r in res.regions] == ["estimated"]
