"""Time /api/risk cold (empty cache, real upstream calls) vs warm (SQLite cache hit).

Usage (from the repo root): python scripts/bench_cache.py [Company ...]
Uses the API keys in .env and writes docs/cache_benchmark.md.
"""

import os
import platform
import statistics
import sys
import tempfile
import time
from collections import Counter
from datetime import date
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)  # the data services resolve data/ relative to the working directory
os.environ["RISK_CACHE_DB"] = os.path.join(tempfile.mkdtemp(prefix="ecotrace-bench-"), "risk_cache.db")

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

COMPANIES = sys.argv[1:] or ["Unilever", "Nestle", "Cargill", "Wilmar", "Mondelez International"]
WARM_REPEATS = 5
UPSTREAMS = {"api.scrapingdog.com": "scrapingdog", "openrouter.ai": "openrouter",
             "data-api.globalforestwatch.org": "gfw"}

calls = Counter()  # (upstream, status) for every outbound request
_send = httpx.AsyncClient.send


async def _counting_send(self, request, *args, **kwargs):
    upstream = UPSTREAMS.get(request.url.host, "company sites")
    try:
        response = await _send(self, request, *args, **kwargs)
    except Exception:
        calls[(upstream, "error")] += 1
        raise
    calls[(upstream, str(response.status_code))] += 1
    return response


httpx.AsyncClient.send = _counting_send


def _calls_cell() -> str:
    by_upstream: dict[str, list[str]] = {}
    for (upstream, status), n in sorted(calls.items()):
        by_upstream.setdefault(upstream, []).append(f"{n}×{status}")
    return "; ".join(f"{u} {', '.join(v)}" for u, v in by_upstream.items())


def main():
    rows, cold_all, warm_all = [], [], []
    with TestClient(app) as client:  # runs the lifespan: loads the datasets, creates the temp cache
        for company in COMPANIES:
            url = f"/api/risk/{quote(company)}"
            calls.clear()
            start = time.perf_counter()
            body = client.get(url).raise_for_status().json()
            cold = time.perf_counter() - start
            outbound = _calls_cell()

            warm = []
            for _ in range(WARM_REPEATS):
                start = time.perf_counter()
                client.get(url).raise_for_status()
                warm.append(time.perf_counter() - start)

            csr = next(s for s in body["sources"] if s["source_name"] == "csr")
            cold_all.append(cold)
            warm_all.extend(warm)
            rows.append((company, cold, statistics.median(warm), max(warm), csr["status"],
                         (csr.get("raw_data") or {}).get("url") or "-", outbound))
            print(f"{company}: cold {cold:.1f} s, warm median {statistics.median(warm) * 1000:.1f} ms, {outbound}")

    lines = [
        "# Cache benchmark: cold vs warm `/api/risk`",
        "",
        f"Run on {date.today().isoformat()} with `python scripts/bench_cache.py` "
        f"(Python {platform.python_version()}, {platform.system()}).",
        "",
        "**Method.** Each company is requested once against an empty, temporary SQLite cache (cold: the real",
        "pipeline with the keys in `.env`, so CSR scraping, the OpenRouter LLM call and GFW run for real), then",
        f"{WARM_REPEATS} more times (warm: served from the 24 h cache). Requests go through FastAPI's TestClient",
        "(in-process ASGI, no TCP), using the GET route because the POST route's limiter allows 20 requests/min.",
        "Outbound calls are counted per upstream and HTTP status.",
        "",
        "| Company | Cold (s) | Warm median (ms) | Warm max (ms) | CSR page | Outbound calls on the cold request |",
        "|---|---|---|---|---|---|",
        *[f"| {c} | {cold:.1f} | {wm * 1000:.1f} | {wx * 1000:.1f} | {status}: {page} | {out} |"
          for c, cold, wm, wx, status, page, out in rows],
        "",
        f"**Cold** (n = {len(cold_all)}): median {statistics.median(cold_all):.1f} s, max {max(cold_all):.1f} s.  ",
        f"**Warm** (n = {len(warm_all)}): median {statistics.median(warm_all) * 1000:.1f} ms, "
        f"max {max(warm_all) * 1000:.1f} ms.",
        "",
        "Cold time depends on how many candidate CSR URLs the scraper probes, one after another, before it finds a",
        "relevant page, so it varies a lot by company. Warm time is the SQLite lookup plus response validation",
        "and serialization; it excludes network round-trips to the API.",
        "",
        "Reading the outbound column: each candidate URL goes to Scrapingdog first and, if that fails (403 = request",
        "refused, for example when the plan's credits are used up), straight to the company site; 403/503 there",
        "usually means bot protection. `gfw 308` means the GFW endpoint redirected; the client does not follow",
        "redirects, so `data/region_risk_fallback.json` supplied the country risk.",
        "",
    ]
    with open(os.path.join(ROOT, "docs", "cache_benchmark.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote docs/cache_benchmark.md")


if __name__ == "__main__":
    main()
