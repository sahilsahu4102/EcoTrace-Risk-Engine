import asyncio
import json
import sqlite3
from unittest.mock import AsyncMock

import httpx
import pytest

from app.services import cache_db
from app.services.forest500_service import Forest500Service
from app.services.gfw_service import GFWService
from app.services.http_retry import MAX_ATTEMPTS
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


def test_trase_matches_every_entity_of_a_group_and_keeps_pairs(tmp_path):
    entities = {
        f"cargill entity {i}": {"names": [f"CARGILL ENTITY {i}"], "total_records": 1, "commodities": ["Soy"],
                                "regions": ["ARGENTINA"], "pairs": [["Soy", "ARGENTINA", 10.0]]}
        for i in range(6)
    }
    entities["cargill cocoa sarl"] = {"names": ["CARGILL COCOA SARL"], "total_records": 1, "commodities": ["Cocoa"],
                                      "regions": ["COTE D'IVOIRE"], "pairs": [["Cocoa", "COTE D'IVOIRE", 99.0]]}
    entities["nestle sa"] = {"names": ["NESTLE SA"], "total_records": 1, "commodities": ["Cocoa"],
                             "regions": ["GHANA"], "pairs": [["Cocoa", "GHANA", 1.0]]}
    entities["cargillo farms"] = {"names": ["CARGILLO FARMS"], "total_records": 1, "commodities": ["Soy"],
                                  "regions": ["BRAZIL"], "pairs": [["Soy", "BRAZIL", 5.0]]}
    data = {"company_names": [n for e in entities.values() for n in e["names"]], "companies": entities}
    svc = TraseService(data_dir=str(tmp_path / "raw"), preprocessed_path=_write_json(tmp_path, "t.json", data))

    res = svc.search("Cargill")

    assert res["matched_entities"] == 7  # all whole-word matches; the old top-5 fuzzy match dropped two
    assert res["pairs"] == [["Cocoa", "COTE D'IVOIRE", 99.0], ["Soy", "ARGENTINA", 60.0]]  # not "cargillo"
    assert svc.search("Nestlé")["matched_names"] == ["NESTLE SA"]


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


def _loss_rows(**loss_by_year):
    return {"data": [{"umd_tree_cover_loss__year": int(y[1:]), "total_loss_ha": v} for y, v in loss_by_year.items()]}


def _gfw_api(loss, alerts=None):
    """Answer GFW queries by dataset: tree cover loss table, or the alerts table."""
    def get(url, **kwargs):
        if "integrated_alerts" in url:
            return alerts if alerts is not None else httpx.Response(200, json={"data": [{"area_ha": None, "latest": None}]})
        return loss
    return get


BASELINE = {f"y{y}": 1_000_000 for y in range(2011, 2021)}


def test_gfw_live_trend_nudges_the_base_risk_and_reports_alerts(gfw, http_get):
    http_get.side_effect = _gfw_api(
        httpx.Response(200, json=_loss_rows(**BASELINE, y2022=500_000, y2023=500_000, y2024=500_000)),
        httpx.Response(200, json={"data": [{"area_ha": 1234.4, "latest": "2026-11-05"}]}),
    )

    first = asyncio.run(gfw.get_tree_loss("bra"))
    second = asyncio.run(gfw.get_tree_loss("BRA"))

    assert first["status"] == "live_api"
    assert first["trend_ratio"] == 0.5  # 2022-24 mean is half the 2011-20 mean
    assert first["normalized_risk"] == 0.9  # base 0.95, trend -50 % -> -0.05
    assert first["recent_years"] == "2022-2024" and first["recent_avg_loss_ha"] == 500_000
    assert (first["alerts_90d_ha"], first["latest_alert"]) == (1234, "2026-11-05")
    assert second == first
    assert http_get.await_count == 2  # loss + alerts once; the second call is cached


def test_gfw_trend_adjustment_is_capped(gfw, http_get):
    http_get.side_effect = _gfw_api(httpx.Response(200, json=_loss_rows(**BASELINE, y2024=9_000_000)))
    res = asyncio.run(gfw.get_tree_loss("BRA"))
    assert res["normalized_risk"] == 1.0  # base 0.95 + at most 0.1, capped at 1


def test_gfw_country_codes_are_validated_before_entering_sql(gfw, http_get):
    assert asyncio.run(gfw.get_tree_loss("BR'; DROP"))["status"] == "unknown"
    http_get.assert_not_awaited()


@pytest.mark.parametrize(
    "outcome",
    [httpx.Response(500, text="boom"), httpx.ReadTimeout("slow")],
    ids=["server-error", "timeout"],
)
def test_gfw_failures_fall_back_to_local_data_without_retry(gfw, http_get, outcome):
    if isinstance(outcome, Exception):
        http_get.side_effect = outcome
    else:
        http_get.return_value = outcome

    res = asyncio.run(gfw.get_tree_loss("BRA"))

    assert res["status"] == "fallback"
    assert res["normalized_risk"] == 0.95
    assert http_get.await_count == 2  # loss and alerts, each tried once
    asyncio.run(gfw.get_tree_loss("BRA"))
    assert http_get.await_count == 4  # fallbacks are not cached, so the next call retries the API


def test_gfw_rate_limit_is_retried_then_falls_back(gfw, http_get):
    http_get.return_value = httpx.Response(429, text="Too Many Requests")
    assert asyncio.run(gfw.get_tree_loss("BRA"))["status"] == "fallback"
    assert http_get.await_count == 2 * MAX_ATTEMPTS


def test_gfw_recovers_after_a_rate_limit(gfw, http_get):
    loss = iter([httpx.Response(429, headers={"Retry-After": "2"}),
                 httpx.Response(200, json=_loss_rows(y2020=10))])
    http_get.side_effect = lambda url, **kw: (
        httpx.Response(200, json={"data": [{}]}) if "integrated_alerts" in url else next(loss)
    )
    assert asyncio.run(gfw.get_tree_loss("BRA"))["status"] == "live_api"


def test_gfw_alerts_failure_keeps_the_live_loss_data(gfw, http_get):
    http_get.side_effect = _gfw_api(httpx.Response(200, json=_loss_rows(**BASELINE)), httpx.Response(500, text="x"))
    res = asyncio.run(gfw.get_tree_loss("BRA"))
    assert res["status"] == "live_api" and res["alerts_90d_ha"] is None


def test_gfw_countries_are_fetched_concurrently(gfw, monkeypatch):
    events = []

    async def fake_tree_loss(iso):
        events.append(f"start {iso}")
        await asyncio.sleep(0)
        events.append(f"end {iso}")
        return {"status": "live_api", "normalized_risk": 0.1}

    monkeypatch.setattr(gfw, "get_tree_loss", fake_tree_loss)
    countries = asyncio.run(gfw.get_countries(["BRA", "IDN", "BRA"]))

    assert list(countries) == ["BRA", "IDN"]  # duplicates fetched once
    assert events[:2] == ["start BRA", "start IDN"]  # both in flight before either finishes


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


def test_scrape_returns_a_relevant_page(monkeypatch):
    scraper = CSRScraper()
    urls = scraper._candidate_urls("Acme Foods")
    relevant = "deforestation sourcing supply chain " * 20
    pages = {urls[2]: {"text": "cookie banner " * 30}, urls[3]: {"text": relevant}}
    fetch = AsyncMock(side_effect=lambda url: pages.get(url))
    monkeypatch.setattr(scraper, "_fetch_and_extract", fetch)

    res = asyncio.run(scraper.scrape("Acme Foods"))

    assert res["status"] == "success"
    assert res["url"] == urls[3]
    assert fetch.await_count == len(urls)  # all candidates are fetched concurrently
    assert res["urls_tried"] == len(urls) <= CSRScraper.MAX_CANDIDATES


def test_scrape_not_found_after_all_candidates(monkeypatch):
    scraper = CSRScraper()
    monkeypatch.setattr(scraper, "_fetch_and_extract", AsyncMock(return_value=None))

    res = asyncio.run(scraper.scrape("Procter Gamble"))

    assert res["status"] == "not_found"
    assert res["urls_tried"] == CSRScraper.MAX_CANDIDATES


def test_scrape_gives_up_when_the_time_budget_runs_out(monkeypatch):
    scraper = CSRScraper()
    scraper.TIME_BUDGET = 0.05

    async def slow(url):
        await asyncio.sleep(5)

    monkeypatch.setattr(scraper, "_fetch_and_extract", slow)
    assert asyncio.run(scraper.scrape("Acme"))["status"] == "not_found"


def test_scrape_caps_text_at_10k_chars(monkeypatch):
    scraper = CSRScraper()
    monkeypatch.setattr(scraper, "_fetch_and_extract",
                        AsyncMock(return_value={"text": "deforestation sourcing supply chain " * 1000}))
    res = asyncio.run(scraper.scrape("Acme"))
    assert len(res["text"]) == 10_000
    assert res["text_length"] > 10_000


def test_candidate_domains_keep_accented_names():
    assert CSRScraper()._generate_domains("Nestlé")[0] == "https://www.nestle.com"


def test_blocked_site_is_read_through_the_reader(http_get):
    scraper = CSRScraper()
    relevant = "Our deforestation policy covers palm oil sourcing and the supply chain. " * 10
    http_get.side_effect = lambda url, **kw: (
        httpx.Response(200, text=relevant) if url.startswith(CSRScraper.READER_URL) else httpx.Response(403, text="denied")
    )

    res = asyncio.run(scraper._fetch_and_extract("https://www.acme.com/sustainability"))

    assert res["source"] == "jina_reader"
    assert http_get.await_count == 2  # one direct attempt, then the reader


def test_reader_error_page_is_not_used(http_get):
    http_get.return_value = httpx.Response(
        200, text="Title: \nWarning: Target URL returned error 404: Not Found " + "x" * 200)
    assert asyncio.run(CSRScraper()._fetch_via_reader("https://www.acme.com/nope")) is None


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


def test_trase_ignores_legal_forms_and_rejects_loose_fuzzy_matches(tmp_path):
    entities = {
        "unilever indonesia": {"names": ["UNILEVER INDONESIA"], "total_records": 1, "commodities": ["Palm Oil"],
                               "regions": ["INDONESIA"], "pairs": [["Palm Oil", "INDONESIA", 9.0]]},
        "universal svs llc": {"names": ["UNIVERSAL SVS LLC"], "total_records": 1, "commodities": ["Beef / Cattle"],
                              "regions": ["BRAZIL"], "pairs": [["Beef / Cattle", "BRAZIL", 1.0]]},
    }
    data = {"company_names": [n for e in entities.values() for n in e["names"]], "companies": entities}
    svc = TraseService(data_dir=str(tmp_path / "raw"), preprocessed_path=_write_json(tmp_path, "t.json", data))

    assert svc.search("Unilever PLC")["matched_names"] == ["UNILEVER INDONESIA"]
    assert svc.search("PT Unilever Tbk")["matched_names"] == ["UNILEVER INDONESIA"]
    assert svc.search("Univerzal Foods")["status"] == "not_found"  # no longer a fuzzy hit


def test_trase_query_is_never_stripped_to_a_generic_word():
    from app.services.trase_service import _strip_legal_forms

    assert _strip_legal_forms("wilmar international limited") == "wilmar"
    assert _strip_legal_forms("marfrig global foods s a") == "marfrig"
    assert _strip_legal_forms("global foods") == "global foods"
