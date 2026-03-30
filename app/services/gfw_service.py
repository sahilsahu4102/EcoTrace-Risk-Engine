"""
Global Forest Watch (GFW) Data Service for Deforestation Risk Scorer.

Queries the GFW Data API to retrieve tree cover loss data by country,
normalizes it into a 0-1 risk score, and provides caching + fallback
to the local region_risk_fallback.json when the API is unavailable.

GFW API: https://data-api.globalforestwatch.org/
"""

import json
import os
import time
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()


class GFWService:
    """Service for querying Global Forest Watch tree cover loss data."""

    # GFW Data API base URL
    BASE_URL = "https://data-api.globalforestwatch.org"

    # Dataset for tree cover loss by country
    DATASET = "umd_tree_cover_loss"
    VERSION = "v1.11"

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
        """Query the GFW Data API for tree cover loss."""
        if not self.api_key:
            print(f"[GFW] No API key configured, using fallback for {iso_code}")
            return None

        url = f"{self.BASE_URL}/dataset/{self.DATASET}/{self.VERSION}/query"

        # SQL query for tree cover loss by year for a country
        sql = (
            f"SELECT umd_tree_cover_loss__year, SUM(umd_tree_cover_loss__ha) as total_loss_ha "
            f"FROM results "
            f"WHERE iso = '{iso_code}' "
            f"GROUP BY umd_tree_cover_loss__year "
            f"ORDER BY umd_tree_cover_loss__year"
        )

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    url,
                    params={"sql": sql},
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_api_response(iso_code, data)
                elif response.status_code == 422 and "require a geometry" in response.text:
                    # GFW API dataset structural change (raster query). Suppress error and use fallback.
                    return None
                else:
                    print(f"[GFW] API error {response.status_code} for {iso_code}: {response.text[:200]}")
                    return None

        except httpx.TimeoutException:
            print(f"[GFW] API timeout for {iso_code}")
            return None
        except Exception as e:
            print(f"[GFW] API error for {iso_code}: {e}")
            return None

    def _parse_api_response(self, iso_code: str, data: dict) -> dict:
        """Parse GFW API response into a normalized result."""
        rows = data.get("data", [])

        if not rows:
            return self._get_fallback(iso_code)

        # Calculate total and recent loss
        total_loss = sum(r.get("total_loss_ha", 0) for r in rows)
        recent_years = [r for r in rows if r.get("umd_tree_cover_loss__year", 0) >= 2018]
        recent_loss = sum(r.get("total_loss_ha", 0) for r in recent_years)

        # Build annual breakdown
        annual = {
            r.get("umd_tree_cover_loss__year"): round(r.get("total_loss_ha", 0), 2)
            for r in rows
        }

        # Normalize to risk score (0-1)
        # Based on Brazil (~2.5M ha/year) as the reference max
        REFERENCE_MAX_ANNUAL = 2_500_000  # ha/year (Brazil benchmark)
        avg_annual = total_loss / max(len(rows), 1)
        normalized_risk = min(avg_annual / REFERENCE_MAX_ANNUAL, 1.0)

        return {
            "status": "live_api",
            "iso_code": iso_code,
            "normalized_risk": round(normalized_risk, 3),
            "total_loss_ha": round(total_loss, 2),
            "recent_loss_ha": round(recent_loss, 2),
            "avg_annual_loss_ha": round(avg_annual, 2),
            "years_covered": len(rows),
            "annual_breakdown": annual,
            "source": "Global Forest Watch API",
        }

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

    async def get_multi_country_risk(self, iso_codes: list[str]) -> dict[str, float]:
        """
        Get normalized risk scores for multiple countries.

        Returns dict mapping ISO codes to normalized risk values (0-1).
        """
        results = {}
        for iso in iso_codes:
            data = await self.get_tree_loss(iso)
            results[iso] = data.get("normalized_risk", 0.5)
        return results

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)
