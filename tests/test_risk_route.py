import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.models.schema import RiskRequest
from app.routes import risk
from app.services import extraction
from app.services.extraction import ExtractionResult, REGIONS, _region_to_dict

NOT_FOUND = {"status": "not_found", "commodities": [], "regions": []}
TRASE_SOY_BRAZIL = {"status": "found", "commodities": ["Soy"], "regions": ["Brazil"], "matched_names": ["ACME"],
                    "total_records": 1, "volumes": {}, "deforestation_indicators": {}}


def _gfw(status="live_api", **risk_by_iso):
    """What GFWService.get_countries returns, for the given ISO -> risk values."""
    return {iso: {"status": status, "normalized_risk": risk} for iso, risk in risk_by_iso.items()}


@pytest.fixture
def sources(cache_db_path, monkeypatch):
    """Every upstream the /api/risk route touches, mocked; defaults to 'nothing found'."""
    src = SimpleNamespace(
        scrape=AsyncMock(return_value={"status": "not_found", "urls_tried": 55}),
        trase=Mock(return_value=NOT_FOUND),
        forest500=Mock(return_value={"status": "not_found", "policy_score": None, "commodities": []}),
        gfw=AsyncMock(return_value={}),
        extract=AsyncMock(return_value=ExtractionResult([], [], [])),
    )
    monkeypatch.setattr(risk.scraper, "scrape", src.scrape)
    monkeypatch.setattr(risk.trase_service, "search", src.trase)
    monkeypatch.setattr(risk.forest500_service, "search", src.forest500)
    monkeypatch.setattr(risk.gfw_service, "get_countries", src.gfw)
    monkeypatch.setattr(extraction, "extract_entities", src.extract)
    return src


def _analyze(company="Acme"):
    return asyncio.run(risk.analyze_risk(RiskRequest(company=company)))


def _status(resp):
    return {s.source_name: s.status for s in resp.sources}


def test_csr_timeout_leaves_other_sources_intact(sources):
    sources.scrape.side_effect = httpx.ReadTimeout("csr timed out")
    sources.trase.return_value = TRASE_SOY_BRAZIL
    sources.forest500.return_value = {"status": "found", "commodities": ["Palm Oil"], "policy_score": 70.0,
                                      "matched_names": ["Acme"], "category_scores": {}, "metadata": {}}
    sources.gfw.return_value = _gfw(BRA=0.8)

    resp = _analyze()

    assert _status(resp) == {"csr": "failed", "trase": "success", "forest500": "success", "gfw": "success"}
    assert next(s for s in resp.sources if s.source_name == "csr").error == "csr timed out"
    assert sorted(c.name for c in resp.commodities) == ["Palm Oil", "Soy"]
    assert [r.name for r in resp.regions] == ["Brazil"]
    assert resp.risk_score == 74.0  # (0.90 * 0.8 + 0.95 * 0.8) / 2 * 100, policy score 70 = no adjustment
    assert resp.flags.no_csr_page_found and not resp.flags.no_trase_data
    sources.gfw.assert_awaited_once_with(["BRA"])


def test_crashing_source_is_isolated(sources):
    sources.trase.side_effect = RuntimeError("corrupt index")
    sources.scrape.return_value = {"status": "success", "url": "https://www.acme.com/sustainability",
                                   "text": "We buy cocoa from Ghana.", "text_length": 24}
    ghana = next(r for r in REGIONS if r.name == "Ghana")
    sources.extract.return_value = ExtractionResult(
        commodities=[{"name": "Cocoa", "risk_weight": 0.8, "matched_keywords": ["cocoa"]}],
        regions=[_region_to_dict(ghana, "estimated", "test")],
        operational_regions=[],
    )
    sources.gfw.return_value = _gfw(GHA=0.5)

    resp = _analyze()

    assert _status(resp)["trase"] == "failed"
    assert next(s for s in resp.sources if s.source_name == "trase").error == "corrupt index"
    assert _status(resp)["csr"] == "success"
    assert [c.name for c in resp.commodities] == ["Cocoa"]
    assert resp.risk_score == 40.0


def test_gfw_failure_falls_back_to_base_region_risk(sources):
    sources.trase.return_value = TRASE_SOY_BRAZIL
    sources.gfw.side_effect = httpx.ConnectError("gfw down")

    resp = _analyze()

    assert _status(resp)["gfw"] == "failed"
    assert resp.flags.no_gfw_data
    assert resp.risk_score == round(0.90 * 0.95 * 100, 1)  # Brazil base_risk 0.95


def test_static_fallback_is_not_reported_as_gfw_responding(sources):
    """Fallback numbers still feed the score, but earn no 'success' and no confidence points."""
    sources.trase.return_value = TRASE_SOY_BRAZIL
    sources.gfw.return_value = _gfw("fallback", BRA=0.95)
    from_fallback = _analyze("Acme")

    sources.gfw.return_value = _gfw(BRA=0.95)
    from_live = _analyze("Acme Live")

    assert _status(from_fallback)["gfw"] == "fallback"
    assert from_fallback.flags.no_gfw_data
    assert from_fallback.risk_score == from_live.risk_score
    assert from_fallback.confidence_score < from_live.confidence_score


def test_mixed_live_and_fallback_countries_are_partial(sources):
    sources.trase.return_value = {**TRASE_SOY_BRAZIL, "regions": ["Brazil", "Indonesia"]}
    sources.gfw.return_value = {**_gfw(BRA=0.8), **_gfw("fallback", IDN=0.9)}

    gfw = next(s for s in _analyze().sources if s.source_name == "gfw")

    assert gfw.status == "partial"
    assert gfw.raw_data["live_countries"] == ["BRA"]


def test_category_search_reports_live_gfw_as_success(sources):
    """_analyze_company_direct dropped the GFW result and always reported 'failed'."""
    sources.trase.return_value = TRASE_SOY_BRAZIL
    sources.gfw.return_value = _gfw(BRA=0.8)

    resp = asyncio.run(risk._analyze_company_direct("Acme", skip_csr=True))

    assert _status(resp)["gfw"] == "success"


def test_repeat_query_is_served_from_cache(sources):
    sources.trase.return_value = TRASE_SOY_BRAZIL
    first = _analyze("Acme")
    for mock in vars(sources).values():
        mock.reset_mock()

    second = _analyze("acme")

    assert second.model_dump() == first.model_dump()
    sources.trase.assert_not_called()
    sources.scrape.assert_not_awaited()
    sources.gfw.assert_not_awaited()


def test_rate_limiter_returns_429_after_20_posts_per_minute():
    from app.main import app, ip_request_counts

    ip_request_counts.clear()
    client = TestClient(app)
    try:
        # POST to a GET-only path: the middleware counts it, the router answers 405 without touching any source
        codes = [client.post("/api/risk/limit-probe").status_code for _ in range(21)]
    finally:
        ip_request_counts.clear()

    assert codes[:20] == [405] * 20
    assert codes[20] == 429
