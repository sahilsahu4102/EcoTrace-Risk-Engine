# Cache benchmark: cold vs warm `/api/risk`

Run on 2026-11-03 with `python scripts/bench_cache.py` (Python 3.13.14, Windows).

**Method.** Each company is requested once against an empty, temporary SQLite cache (cold: the real
pipeline with the keys in `.env`, so CSR scraping, the OpenRouter LLM call and GFW run for real), then
5 more times (warm: served from the 24 h cache). Requests go through FastAPI's TestClient
(in-process ASGI, no TCP), using the GET route because the POST route's limiter allows 20 requests/min.
Outbound calls are counted per upstream and HTTP status.

| Company | Cold (s) | Warm median (ms) | Warm max (ms) | CSR page | Outbound calls on the cold request |
|---|---|---|---|---|---|
| Unilever | 102.9 | 4.2 | 5.7 | not_found: - | company sites 22×403, 11×404, 11×503; gfw 3×308; scrapingdog 44×403 |
| Nestle | 174.1 | 3.2 | 4.7 | not_found: - | company sites 22×403, 22×error; gfw 3×308; scrapingdog 33×403, 11×404 |
| Cargill | 51.7 | 3.5 | 8.1 | not_found: - | company sites 22×403, 22×error; gfw 12×308; scrapingdog 22×403, 22×404 |
| Wilmar | 142.5 | 3.1 | 4.5 | success: https://www.wilmar-international.com/sustainability | company sites 4×200, 22×403, 8×error; gfw 6×308; openrouter 1×200; scrapingdog 34×403 |
| Mondelez International | 52.2 | 2.5 | 2.8 | success: https://www.mondelez.com/sustainability | company sites 1×200, 11×404; gfw 3×308; openrouter 1×200; scrapingdog 12×403 |

**Cold** (n = 5): median 102.9 s, max 174.1 s.  
**Warm** (n = 25): median 3.2 ms, max 8.1 ms.

Cold time depends on how many candidate CSR URLs the scraper probes, one after another, before it finds a
relevant page, so it varies a lot by company. Warm time is the SQLite lookup plus response validation
and serialization; it excludes network round-trips to the API.

Reading the outbound column: each candidate URL goes to Scrapingdog first and, if that fails (403 = request
refused, for example when the plan's credits are used up), straight to the company site; 403/503 there
usually means bot protection. `gfw 308` means the GFW endpoint redirected; the client does not follow
redirects, so `data/region_risk_fallback.json` supplied the country risk.
