"""
Global Forest Watch (GFW) Data Service for Deforestation Risk Scorer.

Queries the GFW Data API to retrieve tree cover loss data by country,
normalizes it into a 0-1 risk score, and provides caching + fallback
to the local region_risk_fallback.json when the API is unavailable.

GFW API: https://data-api.globalforestwatch.org/
"""

import asyncio
import json
import os
import time
from datetime import date, timedelta
from typing import Optional

import httpx
from dotenv import load_dotenv

from app.services.http_retry import with_retry

load_dotenv()


class GFWService:
    """Service for querying Global Forest Watch tree cover loss data."""

    # GFW Data API base URL
    BASE_URL = "https://data-api.globalforestwatch.org"

    # GFW's per-country summary tables (see _query_api)
    DATASET = "gadm__tcl__iso_change"
    ALERTS_DATASET = "gadm__integrated_alerts__iso_daily_alerts"
    VERSION = "latest"
    ALERT_WINDOW_DAYS = 90
    MAX_TREND_ADJUSTMENT = 0.1

    # Cache TTL in seconds (1 hour)
    CACHE_TTL = 3600

    def __init__(self):
        self.api_key = os.getenv("GFW_API_KEY", "")
        self._cache: dict[str, dict] = {}
        self._cache_timestamps: dict[str, float] = {}
        self._fallback_data: Optional[dict] = None
        self._load_fallback()

    def _load_fallback(self):
        """Load fallback region risk data from JSON file."""
        fallback_path = os.path.join("data", "region_risk_fallback.json")
        try:
            abs_path = os.path.abspath(fallback_path)
            with open(abs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._fallback_data = {
                    r["iso"]: r for r in data.get("regions", [])
                }
            print(f"[GFW] Loaded fallback data: {len(self._fallback_data)} countries")
        except Exception as e:
            print(f"[GFW] Failed to load fallback data: {e}")
            self._fallback_data = {}

    async def get_tree_loss(self, iso_code: str) -> dict:
        """
        Get tree cover loss data for a country by ISO code.

        Tries the GFW API first, falls back to local data if API fails.

        Args:
            iso_code: ISO 3166-1 alpha-3 country code (e.g., 'BRA', 'IDN')

        Returns:
            Dict with risk score, total loss, annual breakdown, and source info.
        """
        iso_code = iso_code.upper()

        # Check cache first
        cached = self._get_from_cache(iso_code)
        if cached is not None:
            return cached

        # Try GFW API
        api_result = await self._query_api(iso_code)
        if api_result is not None:
            self._set_cache(iso_code, api_result)
            return api_result

        # Fallback to local data
        fallback = self._get_fallback(iso_code)
        return fallback

    async def _query_api(self, iso_code: str) -> Optional[dict]:
        """Yearly tree cover loss and recent deforestation alerts for one country.

        Until 2026-11 this queried the raster dataset `umd_tree_cover_loss`, which
        refuses country queries without a geometry (HTTP 422), so every request fell
        back to static data. The `gadm__*__iso_*` tables are GFW's own per-country
        summaries of the same UMD data and of the integrated (GLAD-L, GLAD-S2, RADD)
        alerts. Their `latest` version redirects to the current one.
        """
        if not self.api_key:
            print(f"[GFW] No API key configured, using fallback for {iso_code}")
            return None
        if not (len(iso_code) == 3 and iso_code.isalpha()):  # it is put into SQL below
            return None

        loss_sql = (
            "SELECT umd_tree_cover_loss__year, SUM(umd_tree_cover_loss__ha) AS total_loss_ha FROM data "
            f"WHERE iso = '{iso_code}' AND umd_tree_cover_density_2000__threshold = 30 "
            "GROUP BY umd_tree_cover_loss__year ORDER BY umd_tree_cover_loss__year"
        )
        since = (date.today() - timedelta(days=self.ALERT_WINDOW_DAYS)).isoformat()
        # Natural forest only, as GFW's dashboards report it: most alert area in the
        # table is on unclassified land (4.3 M of India's 4.4 M ha over 90 days), which
        # would present crop and land-cover changes as deforestation.
        alerts_sql = (
            "SELECT SUM(alert_area__ha) AS area_ha, MAX(gfw_integrated_alerts__date) AS latest FROM data "
            f"WHERE iso = '{iso_code}' AND gfw_integrated_alerts__date >= '{since}' "
            "AND gfw_integrated_alerts__confidence IN ('high', 'highest') "
            "AND sbtn_natural_forests__class = 'Natural Forest'"
        )
        headers = {"x-api-key": self.api_key}

        def query(dataset: str, sql: str):
            url = f"{self.BASE_URL}/dataset/{dataset}/{self.VERSION}/query/json"
            return with_retry(lambda: client.get(url, params={"sql": sql}, headers=headers))

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                loss, alerts = await asyncio.gather(
                    query(self.DATASET, loss_sql), query(self.ALERTS_DATASET, alerts_sql),
                    return_exceptions=True,
                )
        except Exception as e:
            print(f"[GFW] API error for {iso_code}: {e}")
            return None

        if isinstance(loss, Exception) or loss.status_code != 200:
            detail = loss if isinstance(loss, Exception) else f"{loss.status_code}: {loss.text[:200]}"
            print(f"[GFW] tree cover loss query failed for {iso_code}: {detail}")
            return None

        alert_row = {}
        if not isinstance(alerts, Exception) and alerts.status_code == 200:
            alert_row = (alerts.json().get("data") or [{}])[0] or {}
        return self._parse_api_response(iso_code, loss.json(), alert_row)

    def _parse_api_response(self, iso_code: str, data: dict, alerts: Optional[dict] = None) -> dict:
        """Region risk = the country's expert base risk, nudged by its loss trend.

        Until 2026-11 the risk was average yearly loss divided by Brazil's 2.5 M ha,
        which put a small, fast-clearing country like Ghana near zero. Now the
        base risk (region_risk_fallback.json) stays the anchor and the live data
        moves it by up to +/-0.1: the mean loss of the last 3 years against the
        country's own 2011-2020 mean. Alerts are reported, not scored.
        """
        annual = {
            int(r["umd_tree_cover_loss__year"]): round(r.get("total_loss_ha") or 0, 2)
            for r in data.get("data", [])
            if r.get("umd_tree_cover_loss__year")
        }
        if not annual:
            return self._get_fallback(iso_code)

        years = sorted(annual)
        recent_years = years[-3:]
        recent_avg = sum(annual[y] for y in recent_years) / len(recent_years)
        baseline = [annual[y] for y in years if 2011 <= y <= 2020]
        baseline_avg = sum(baseline) / len(baseline) if baseline else 0.0
        trend = recent_avg / baseline_avg if baseline_avg else 1.0
        adjustment = max(-self.MAX_TREND_ADJUSTMENT, min(self.MAX_TREND_ADJUSTMENT, (trend - 1) * 0.1))
        base = self._base_risk(iso_code)

        alerts = alerts or {}
        return {
            "status": "live_api",
            "iso_code": iso_code,
            "normalized_risk": round(min(max(base + adjustment, 0.0), 1.0), 3),
            "base_risk": base,
            "trend_ratio": round(trend, 2),
            "recent_years": f"{recent_years[0]}-{recent_years[-1]}",
            "recent_avg_loss_ha": round(recent_avg),
            "baseline_avg_loss_ha": round(baseline_avg) if baseline_avg else None,
            "total_loss_ha": round(sum(annual.values()), 2),
            "recent_loss_ha": round(sum(v for y, v in annual.items() if y >= 2018), 2),
            "avg_annual_loss_ha": round(sum(annual.values()) / len(annual), 2),
            "years_covered": len(annual),
            "annual_breakdown": annual,
            "alerts_90d_ha": round(alerts["area_ha"]) if alerts.get("area_ha") is not None else None,
            "latest_alert": alerts.get("latest"),
            "source": "Global Forest Watch Data API",
        }

    def _base_risk(self, iso_code: str) -> float:
        region = (self._fallback_data or {}).get(iso_code) or {}
        return region.get("base_risk", 0.5)

    def _get_fallback(self, iso_code: str) -> dict:
        """Get fallback data for a country."""
        if self._fallback_data and iso_code in self._fallback_data:
            region = self._fallback_data[iso_code]
            return {
                "status": "fallback",
                "iso_code": iso_code,
                "normalized_risk": region.get("base_risk", 0.5),
                "total_loss_ha": region.get("tree_cover_loss_mha", 0) * 1_000_000,
                "recent_loss_ha": None,
                "avg_annual_loss_ha": None,
                "years_covered": 0,
                "annual_breakdown": {},
                "source": "Local fallback data (region_risk_fallback.json)",
            }

        return {
            "status": "unknown",
            "iso_code": iso_code,
            "normalized_risk": 0.5,
            "total_loss_ha": None,
            "recent_loss_ha": None,
            "avg_annual_loss_ha": None,
            "years_covered": 0,
            "annual_breakdown": {},
            "source": "Default (country not in database)",
        }

    def _get_from_cache(self, iso_code: str) -> Optional[dict]:
        """Get data from cache if not expired."""
        if iso_code in self._cache:
            timestamp = self._cache_timestamps.get(iso_code, 0)
            if time.time() - timestamp < self.CACHE_TTL:
                return self._cache[iso_code]
            else:
                # Expired — remove
                del self._cache[iso_code]
                del self._cache_timestamps[iso_code]
        return None

    def _set_cache(self, iso_code: str, data: dict):
        """Store data in cache with current timestamp."""
        self._cache[iso_code] = data
        self._cache_timestamps[iso_code] = time.time()

    async def get_countries(self, iso_codes: list[str]) -> dict[str, dict]:
        """Full tree-loss result per country, fetched concurrently.

        Each country is an independent API call with its own 15 s timeout, so
        querying them one after another made a five-country request wait for
        five timeouts in a row when the API was down.
        """
        unique = list(dict.fromkeys(iso_codes))
        results = await asyncio.gather(*(self.get_tree_loss(iso) for iso in unique))
        return dict(zip(unique, results))

    async def get_multi_country_risk(self, iso_codes: list[str]) -> dict[str, float]:
        """Normalized risk (0-1) per ISO code."""
        countries = await self.get_countries(iso_codes)
        return {iso: data.get("normalized_risk", 0.5) for iso, data in countries.items()}

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)
