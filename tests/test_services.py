import asyncio
import json
import sqlite3
from unittest.mock import AsyncMock

import httpx
import pytest

from app.services import cache_db
from app.services.forest500_service import Forest500Service
from app.services.gfw_service import GFWService
from app.services.scraper import CSRScraper
from app.services.trase_service import TraseService


def _write_json(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------- Trase

TRASE_DATA = {
    "company_names": ["Cargill Agricola", "Cargill Agricola SA", "Bunge Alimentos"],
    "companies": {
        "cargill agricola": {
            "names": ["CARGILL AGRICOLA"], "total_records": 3, "commodities": ["Soy"], "regions": ["Brazil"],
            "volumes": {"volume": {"total": 10.0, "records": 3}},
            "deforestation_indicators": {"soy_deforestation_exposure": {"total": 1.5, "max": 1.0, "records": 3}},
        },
        "cargill agricola sa": {
            "names": ["CARGILL AGRICOLA S.A."], "total_records": 2, "commodities": ["Soy", "Beef / Cattle"],
            "regions": ["Paraguay"],
            "volumes": {"volume": {"total": 5.25, "records": 2}},
            "deforestation_indicators": {"soy_deforestation_exposure": {"total": 0.5, "max": 2.0, "records": 2}},
        },
        "bunge alimentos": {
            "names": ["BUNGE ALIMENTOS"], "total_records": 1, "commodities": ["Soy"], "regions": ["Argentina"],
            "volumes": {}, "deforestation_indicators": {},
        },
    },
}


@pytest.fixture
def trase(tmp_path):
    return TraseService(data_dir=str(tmp_path / "raw"), preprocessed_path=_write_json(tmp_path, "trase.json", TRASE_DATA))


def test_trase_aggregates_all_fuzzy_matches(trase):
    res = trase.search("Cargill Agricola")

    assert res["status"] == "found"
    assert res["matched_names"] == ["CARGILL AGRICOLA", "CARGILL AGRICOLA S.A."]
    assert res["total_records"] == 5
    assert res["commodities"] == ["Beef / Cattle", "Soy"]
    assert res["regions"] == ["Brazil", "Paraguay"]
    assert res["volumes"] == {"volume": {"total": 15.25, "records": 5}}
    assert res["deforestation_indicators"]["soy_deforestation_exposure"] == {"total": 2.0, "max": 2.0, "records": 5}


def test_trase_search_does_not_mutate_loaded_data(trase):
    assert trase.search("Cargill Agricola") == trase.search("Cargill Agricola")


def test_trase_unknown_company(trase):
    res = trase.search("Totally Unrelated Widgets")
    assert res["status"] == "not_found"
    assert res["commodities"] == [] and res["regions"] == []


def test_trase_without_data_reports_not_available(tmp_path):
    svc = TraseService(data_dir=str(tmp_path / "missing"), preprocessed_path=str(tmp_path / "missing.json"))
    assert svc.search("Cargill")["status"] == "not_available"


def test_committed_preprocessed_datasets_load():
    trase, forest500 = TraseService(), Forest500Service()
    assert trase.load() and trase.company_count > 0
    assert forest500.load() and forest500.company_count > 0
    assert trase.search(trase._company_names[0])["status"] == "found"


# ---------------------------------------------------------------- Forest 500

FOREST500_DATA = {
    "company_names": ["Unilever", "Unilever PLC"],
    "companies": {
        "unilever": {"names": ["Unilever"], "total_records": 1, "commodities": ["Palm Oil"], "policy_score": None,
                     "category_scores": {"commitment": 10.0}, "metadata": {"sector": "Consumer goods"}},
        "unilever plc": {"names": ["Unilever PLC"], "total_records": 1, "commodities": ["Soy"], "policy_score": 42.0,
                         "category_scores": {"commitment": 99.0, "reporting": 5.0}, "metadata": {"sector": "Other"}},
    },
}


def test_forest500_merges_matches_first_non_null_wins(tmp_path):
    svc = Forest500Service(preprocessed_path=_write_json(tmp_path, "f500.json", FOREST500_DATA))

    res = svc.search("Unilever")

    assert res["status"] == "found"
    assert res["policy_score"] == 42.0
    assert res["commodities"] == ["Palm Oil", "Soy"]
    assert res["category_scores"] == {"commitment": 10.0, "reporting": 5.0}
    assert res["metadata"] == {"sector": "Consumer goods"}


def test_forest500_unknown_company(tmp_path):
    svc = Forest500Service(preprocessed_path=_write_json(tmp_path, "f500.json", FOREST500_DATA))
    res = svc.search("Totally Unrelated Widgets")
    assert res["status"] == "not_found" and res["policy_score"] is None


# ---------------------------------------------------------------- Global Forest Watch

@pytest.fixture
def gfw():
    svc = GFWService()
    svc.api_key = "test-key"
    svc._fallback_data = {"BRA": {"iso": "BRA", "base_risk": 0.95, "tree_cover_loss_mha": 1.5}}
    return svc


@pytest.fixture
def http_get(monkeypatch):
    get = AsyncMock()
    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    return get


def test_gfw_live_response_is_normalized_and_cached(gfw, http_get):
    http_get.return_value = httpx.Response(200, json={"data": [
        {"umd_tree_cover_loss__year": 2017, "total_loss_ha": 1_000_000},
        {"umd_tree_cover_loss__year": 2019, "total_loss_ha": 3_000_000},
    ]})

    first = asyncio.run(gfw.get_tree_loss("bra"))
    second = asyncio.run(gfw.get_tree_loss("BRA"))

    assert first["status"] == "live_api"
    assert first["total_loss_ha"] == 4_000_000
    assert first["recent_loss_ha"] == 3_000_000
    assert first["normalized_risk"] == 0.8  # 2M ha/yr average vs 2.5M reference
    assert second == first
    assert http_get.await_count == 1


@pytest.mark.parametrize(
    "outcome",
    [httpx.Response(429, text="Too Many Requests"), httpx.Response(500, text="boom"), httpx.ReadTimeout("slow")],
    ids=["rate-limited", "server-error", "timeout"],
)
def test_gfw_failures_fall_back_to_local_data_without_retry(gfw, http_get, outcome):
    if isinstance(outcome, Exception):
        http_get.side_effect = outcome
    else:
        http_get.return_value = outcome

    res = asyncio.run(gfw.get_tree_loss("BRA"))

    assert res["status"] == "fallback"
    assert res["normalized_risk"] == 0.95
    assert http_get.await_count == 1
    asyncio.run(gfw.get_tree_loss("BRA"))
    assert http_get.await_count == 2  # fallbacks are not cached, so the next call retries the API


def test_gfw_without_key_never_calls_api(gfw, http_get):
    gfw.api_key = ""
    assert asyncio.run(gfw.get_tree_loss("BRA"))["status"] == "fallback"
    unknown = asyncio.run(gfw.get_tree_loss("XXX"))
    assert unknown["status"] == "unknown" and unknown["normalized_risk"] == 0.5
    http_get.assert_not_awaited()


def test_gfw_multi_country_returns_risk_per_iso(gfw, http_get):
    gfw.api_key = ""
    assert asyncio.run(gfw.get_multi_country_risk(["BRA", "XXX"])) == {"BRA": 0.95, "XXX": 0.5}


# ---------------------------------------------------------------- CSR scraper

RELEVANT_HTML = (
    "<html><head><script>var x = 'palm oil';</script></head><body><nav>Menu sustainability</nav>"
    "<p>" + "Our sustainability report covers deforestation, sourcing and our supply chain. " * 5 + "</p>"
    "<footer>Footer climate</footer></body></html>"
)


def test_scrape_returns_first_relevant_page(monkeypatch):
    scraper = CSRScraper()
    urls = [p.format(domain=d) for d in scraper._generate_domains("Acme Foods") for p in scraper.URL_PATTERNS]
    relevant = "deforestation sourcing supply chain " * 20
    pages = {urls[2]: {"text": "cookie banner " * 30}, urls[3]: {"text": relevant}}
    fetch = AsyncMock(side_effect=lambda url: pages.get(url))
    monkeypatch.setattr(scraper, "_fetch_and_extract", fetch)

    res = asyncio.run(scraper.scrape("Acme Foods"))

    assert res["status"] == "success"
    assert res["url"] == urls[3]
    assert fetch.await_count == 4  # stops at the first relevant page
    assert res["urls_tried"] == len(urls)


def test_scrape_not_found_after_all_candidates(monkeypatch):
    scraper = CSRScraper()
    monkeypatch.setattr(scraper, "_fetch_and_extract", AsyncMock(return_value=None))

    res = asyncio.run(scraper.scrape("Procter Gamble"))

    assert res["status"] == "not_found"
    assert res["urls_tried"] == 5 * len(CSRScraper.URL_PATTERNS)  # 5 candidate domains


def test_scrape_caps_text_at_10k_chars(monkeypatch):
    scraper = CSRScraper()
    monkeypatch.setattr(scraper, "_fetch_and_extract",
                        AsyncMock(return_value={"text": "deforestation sourcing supply chain " * 1000}))
    res = asyncio.run(scraper.scrape("Acme"))
    assert len(res["text"]) == 10_000
    assert res["text_length"] > 10_000


def test_scrapingdog_rate_limit_falls_back_to_direct_fetch(http_get):
    scraper = CSRScraper()
    scraper.api_key = "test-key"
    http_get.side_effect = lambda url, **kw: (
        httpx.Response(429, text="Limit reached") if "scrapingdog" in url else httpx.Response(200, text=RELEVANT_HTML)
    )

    res = asyncio.run(scraper._fetch_and_extract("https://www.acme.com/sustainability"))

    assert res["source"] == "direct"
    assert http_get.await_count == 2


def test_extract_text_drops_scripts_and_page_chrome():
    text = CSRScraper()._extract_text(RELEVANT_HTML)
    assert "var x" not in text and "Menu" not in text and "Footer" not in text
    assert text.startswith("Our sustainability report")


def test_relevance_needs_three_keywords_and_200_chars():
    scraper = CSRScraper()
    assert not scraper._is_relevant("cocoa coffee " * 20)  # 2 keywords
    assert scraper._is_relevant("cocoa coffee rubber " * 20)
    assert not scraper._is_relevant("cocoa coffee rubber")  # too short


# ---------------------------------------------------------------- SQLite cache

def _save(query, score=50.0):
    cache_db.save_cached_risk(query, score, "moderate", 60.0, "moderate", {"company": query, "risk_score": score})


def test_cache_miss_then_case_insensitive_hit(cache_db_path):
    assert cache_db.get_cached_risk("Unilever") is None
    _save("Unilever")
    assert cache_db.get_cached_risk("unilever") == {"company": "Unilever", "risk_score": 50.0}


def test_cache_upsert_keeps_latest(cache_db_path):
    _save("Unilever", 50.0)
    _save("Unilever", 70.0)
    assert cache_db.get_cached_risk("Unilever")["risk_score"] == 70.0
    assert len(cache_db.get_recent_history()) == 1


def test_cache_entries_expire_after_a_day(cache_db_path):
    _save("Unilever")
    with sqlite3.connect(cache_db_path) as conn:
        conn.execute("UPDATE risk_cache SET created_at = datetime('now', '-25 hours')")
    assert cache_db.get_cached_risk("Unilever") is None


def test_recent_history_is_newest_first_and_limited(cache_db_path):
    for i, q in enumerate(["A", "B", "C"]):
        _save(q)
        with sqlite3.connect(cache_db_path) as conn:
            conn.execute("UPDATE risk_cache SET created_at = datetime('now', ?) WHERE query = ?", (f"-{10 - i} minutes", q))
    assert [r["query"] for r in cache_db.get_recent_history(2)] == ["C", "B"]
