"""
CSR Page Scraper for Deforestation Risk Scorer.

Generates candidate sustainability/ESG page URLs for a company,
fetches them via Scrapingdog API (or direct HTTP), and extracts
relevant text for entity extraction.

Scrapingdog: https://scrapingdog.com/
"""

import os
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


class CSRScraper:
    """Scrapes corporate sustainability/CSR pages for deforestation-relevant text."""

    # Common CSR/sustainability page URL patterns
    URL_PATTERNS = [
        "{domain}/sustainability",
        "{domain}/esg",
        "{domain}/csr",
        "{domain}/environment",
        "{domain}/responsibility",
        "{domain}/sustainable-sourcing",
        "{domain}/supply-chain",
        "{domain}/deforestation",
        "{domain}/palm-oil",
        "{domain}/sustainable-development",
        "{domain}/environmental-policy",
    ]

    # Keywords indicating relevant content
    RELEVANCE_KEYWORDS = [
        "deforestation", "forest", "palm oil", "soy", "beef", "cattle",
        "cocoa", "coffee", "rubber", "timber", "supply chain", "sourcing",
        "sustainability", "environmental", "biodiversity", "land use",
        "carbon", "emissions", "climate", "renewable", "rspo", "ndpe",
        "zero deforestation", "no deforestation", "commodity",
    ]

    def __init__(self):
        self.api_key = os.getenv("SCRAPINGDOG_API_KEY", "")
        self._timeout = 12.0

    async def scrape(self, company: str) -> dict:
        """
        Scrape CSR/sustainability pages for a company.

        Args:
            company: Company name (e.g., "Unilever")

        Returns:
            Dict with status, extracted text, URLs tried, and URL that worked.
        """
        # Generate candidate domains
        domains = self._generate_domains(company)

        # Generate all candidate URLs
        candidate_urls = []
        for domain in domains:
            for pattern in self.URL_PATTERNS:
                candidate_urls.append(pattern.format(domain=domain))

        # Try fetching each URL
        for url in candidate_urls:
            result = await self._fetch_and_extract(url)
            if result is not None:
                text = result["text"]
                # Check if the content is relevant
                if self._is_relevant(text):
                    return {
                        "status": "success",
                        "company": company,
                        "url": url,
                        "text": text[:10000],  # Cap text length
                        "text_length": len(text),
                        "urls_tried": len(candidate_urls),
                    }

        return {
            "status": "not_found",
            "company": company,
            "url": None,
            "text": "",
            "text_length": 0,
            "urls_tried": len(candidate_urls),
        }

    def _generate_domains(self, company: str) -> list[str]:
        """Generate candidate domain URLs for a company."""
        # Normalize company name
        clean = re.sub(r"[^a-zA-Z0-9\s]", "", company).strip().lower()
        parts = clean.split()

        domains = []

        # Full name concatenated: unilever.com
        full = "".join(parts)
        domains.append(f"https://www.{full}.com")

        # First word only: cargill.com
        if parts:
            domains.append(f"https://www.{parts[0]}.com")

        # Hyphenated: procter-gamble.com
        if len(parts) > 1:
            hyphenated = "-".join(parts)
            domains.append(f"https://www.{hyphenated}.com")

        # With "group": wilmar-group.com
        if parts:
            domains.append(f"https://www.{parts[0]}group.com")
            domains.append(f"https://www.{parts[0]}-international.com")

        return domains

    async def _fetch_and_extract(self, url: str) -> Optional[dict]:
        """Fetch a URL and extract text content."""
        # Try Scrapingdog first if API key is available
        if self.api_key:
            result = await self._fetch_via_scrapingdog(url)
            if result is not None:
                return result

        # Fallback to direct HTTP
        return await self._fetch_direct(url)

    async def _fetch_via_scrapingdog(self, url: str) -> Optional[dict]:
        """Fetch URL via Scrapingdog API for JavaScript-rendered pages."""
        scrapingdog_url = "https://api.scrapingdog.com/scrape"
        params = {
            "api_key": self.api_key,
            "url": url,
            "dynamic": "true",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(scrapingdog_url, params=params)
                if response.status_code == 200:
                    text = self._extract_text(response.text)
                    if text and len(text) > 100:
                        return {"text": text, "source": "scrapingdog"}
        except Exception:
            pass

        return None

    async def _fetch_direct(self, url: str) -> Optional[dict]:
        """Fetch URL via direct HTTP request."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                verify=False,  # Some corporate sites have cert issues
            ) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    text = self._extract_text(response.text)
                    if text and len(text) > 100:
                        return {"text": text, "source": "direct"}
        except Exception:
            pass

        return None

    def _extract_text(self, html: str) -> str:
        """Extract meaningful text from HTML content."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove script, style, nav, footer, header tags
        for tag in soup(["script", "style", "nav", "footer", "header", "meta", "link"]):
            tag.decompose()

        # Get text
        text = soup.get_text(separator=" ", strip=True)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _is_relevant(self, text: str) -> bool:
        """Check if extracted text contains deforestation-relevant content."""
        if len(text) < 200:
            return False

        text_lower = text.lower()
        matches = sum(1 for kw in self.RELEVANCE_KEYWORDS if kw in text_lower)

        # Require at least 3 relevant keywords
        return matches >= 3

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)
