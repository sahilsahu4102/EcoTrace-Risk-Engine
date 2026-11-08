"""
CSR Page Scraper for Deforestation Risk Scorer.

Guesses a company's sustainability page URLs, fetches them concurrently, and
returns the first page with deforestation-relevant text for entity extraction.

Each URL is fetched directly first; when the site blocks scripts or renders with
JavaScript, the free Jina Reader (https://r.jina.ai/) fetches it in a real browser
and returns the page as text. Until 2026-11 the fallback was Scrapingdog, whose
free plan allows no requests, and 44 URLs were tried one after another: about
37 s per analysis that always ended in "not found".
"""

import asyncio
import re
import unicodedata
from typing import Optional

import httpx
from bs4 import BeautifulSoup


class CSRScraper:
    """Finds and reads corporate sustainability/CSR pages."""

    # Tried on every candidate domain; EXTRA_PATHS only on the most likely one
    PRIMARY_PATH = "/sustainability"
    EXTRA_PATHS = ["/esg", "/en/sustainability"]
    MAX_CANDIDATES = 6

    READER_URL = "https://r.jina.ai/"
    DIRECT_TIMEOUT = 8.0
    READER_TIMEOUT = 20.0
    TIME_BUDGET = 25.0  # the whole CSR source, all candidates included

    # Keywords indicating relevant content
    RELEVANCE_KEYWORDS = [
        "deforestation", "forest", "palm oil", "soy", "beef", "cattle",
        "cocoa", "coffee", "rubber", "timber", "supply chain", "sourcing",
        "sustainability", "environmental", "biodiversity", "land use",
        "carbon", "emissions", "climate", "renewable", "rspo", "ndpe",
        "zero deforestation", "no deforestation", "commodity",
    ]

    async def scrape(self, company: str) -> dict:
        """
        Find a relevant CSR/sustainability page for a company.

        Args:
            company: Company name (e.g., "Unilever")

        Returns:
            Dict with status, extracted text, URLs tried, and the URL that worked.
        """
        urls = self._candidate_urls(company)

        async def attempt(url: str):
            return url, await self._fetch_and_extract(url)

        tasks = [asyncio.create_task(attempt(u)) for u in urls]
        try:
            for finished in asyncio.as_completed(tasks, timeout=self.TIME_BUDGET):
                url, result = await finished
                if result is not None and self._is_relevant(result["text"]):
                    text = result["text"]
                    return {
                        "status": "success",
                        "company": company,
                        "url": url,
                        "text": text[:10000],  # Cap text length
                        "text_length": len(text),
                        "urls_tried": len(urls),
                        "fetched_via": result.get("source"),
                    }
        except asyncio.TimeoutError:
            pass
        finally:
            for task in tasks:
                task.cancel()

        return {
            "status": "not_found",
            "company": company,
            "url": None,
            "text": "",
            "text_length": 0,
            "urls_tried": len(urls),
        }

    def _candidate_urls(self, company: str) -> list[str]:
        domains = self._generate_domains(company)
        if not domains:
            return []
        urls = [d + self.PRIMARY_PATH for d in domains] + [domains[0] + p for p in self.EXTRA_PATHS]
        return list(dict.fromkeys(urls))[: self.MAX_CANDIDATES]

    def _generate_domains(self, company: str) -> list[str]:
        """Generate candidate domain URLs for a company."""
        # Normalize: "Nestlé" -> "nestle" (the old ASCII-only filter made it "nestl")
        ascii_name = unicodedata.normalize("NFKD", company).encode("ascii", "ignore").decode()
        clean = re.sub(r"[^a-zA-Z0-9\s]", "", ascii_name).strip().lower()
        parts = clean.split()

        domains = []

        # Full name concatenated: unilever.com
        full = "".join(parts)
        if full:
            domains.append(f"https://www.{full}.com")

        # First word only: cargill.com
        if parts:
            domains.append(f"https://www.{parts[0]}.com")

        # Hyphenated: procter-gamble.com
        if len(parts) > 1:
            domains.append(f"https://www.{'-'.join(parts)}.com")

        # Group and international sites: wilmar-international.com
        if parts:
            domains.append(f"https://www.{parts[0]}group.com")
            domains.append(f"https://www.{parts[0]}-international.com")

        return list(dict.fromkeys(domains))

    async def _fetch_and_extract(self, url: str) -> Optional[dict]:
        """Fetch a URL directly; if that fails or yields no relevant text, through the reader."""
        direct = await self._fetch_direct(url)
        if direct is not None and self._is_relevant(direct["text"]):
            return direct
        return await self._fetch_via_reader(url) or direct

    async def _fetch_via_reader(self, url: str) -> Optional[dict]:
        """Fetch a page through the Jina Reader, which renders it and returns text."""
        try:
            async with httpx.AsyncClient(timeout=self.READER_TIMEOUT) as client:
                response = await client.get(
                    self.READER_URL + url, headers={"Accept": "text/plain", "X-Return-Format": "text"}
                )
        except Exception:
            return None
        text = re.sub(r"\s+", " ", response.text).strip() if response.status_code == 200 else ""
        # The reader answers 200 with a warning when the target page itself failed
        if len(text) < 100 or "returned error 4" in text[:600] or "returned error 5" in text[:600]:
            return None
        return {"text": text, "source": "jina_reader"}

    async def _fetch_direct(self, url: str) -> Optional[dict]:
        """Fetch URL via direct HTTP request."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.DIRECT_TIMEOUT,
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
