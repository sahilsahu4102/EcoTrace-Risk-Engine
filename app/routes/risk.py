"""
Risk Analysis API Route for Deforestation Risk Scorer.

The /api/risk endpoint orchestrates all data sources concurrently,
runs extraction and scoring, and returns a comprehensive risk assessment.
"""

import asyncio

from fastapi import APIRouter, HTTPException

from app.models.schema import (
    RiskRequest,
    RiskResponse,
    CommodityDetail,
    RegionDetail,
    CommodityRegionBreakdown,
    SourceResult,
    DisclosureFlags,
)
from app.services.extraction import extract_entities
from app.services.scraper import CSRScraper
from app.services.trase_service import TraseService
from app.services.forest500_service import Forest500Service
from app.services.gfw_service import GFWService
from app.utils.scoring import (
    compute_risk_score,
    get_risk_level,
    compute_confidence_score,
    get_confidence_level,
    generate_summary,
)

router = APIRouter(prefix="/api", tags=["Risk Analysis"])

# Service singletons (initialized on import, data loaded via lifespan)
scraper = CSRScraper()
trase_service = TraseService()
forest500_service = Forest500Service()
gfw_service = GFWService()


def load_data_services():
    """Load CSV data into memory. Called during app startup."""
    trase_service.load()
    forest500_service.load()


@router.post("/risk", response_model=RiskResponse)
async def analyze_risk(request: RiskRequest):
    """
    Analyze deforestation risk for a company.

    Orchestrates 4 data sources concurrently:
    1. CSR page scraping (Scrapingdog / direct HTTP)
    2. Trase supply chain data (CSV)
    3. Forest 500 policy rankings (CSV)
    4. Global Forest Watch tree cover loss (API)

    Returns a comprehensive risk assessment with score, confidence,
    commodity/region breakdown, and disclosure flags.
    """
    company = request.company.strip()

    # Run all data sources concurrently
    csr_task = asyncio.create_task(_get_csr_data(company))
    trase_task = asyncio.create_task(_get_trase_data(company))
    forest500_task = asyncio.create_task(_get_forest500_data(company))

    csr_result, trase_result, forest500_result = await asyncio.gather(
        csr_task, trase_task, forest500_task,
        return_exceptions=True,
    )

    # Handle exceptions from gather
    if isinstance(csr_result, Exception):
        csr_result = _error_source("csr", str(csr_result))
    if isinstance(trase_result, Exception):
        trase_result = _error_source("trase", str(trase_result))
    if isinstance(forest500_result, Exception):
        forest500_result = _error_source("forest500", str(forest500_result))

    # Aggregate all extracted text for entity extraction
    all_text = _aggregate_text(company, csr_result, trase_result, forest500_result)

    # Run entity extraction
    extraction = extract_entities(all_text)

    # Get GFW data for detected regions
    gfw_overrides = {}
    gfw_result = _error_source("gfw", "No regions detected")
    if extraction.regions:
        iso_codes = [r["iso_code"] for r in extraction.regions]
        try:
            gfw_overrides = await gfw_service.get_multi_country_risk(iso_codes)
            gfw_result = {
                "source_name": "gfw",
                "status": "success",
                "commodities_found": [],
                "regions_found": list(gfw_overrides.keys()),
                "raw_data": {"risk_by_country": gfw_overrides},
            }
        except Exception as e:
            gfw_result = _error_source("gfw", str(e))

    # Get Forest 500 policy score for scoring adjustment
    forest500_score = None
    if isinstance(forest500_result, dict) and forest500_result.get("status") == "success":
        raw = forest500_result.get("raw_data", {})
        forest500_score = raw.get("policy_score")

    # Compute risk score
    risk_score, breakdown = compute_risk_score(
        extraction.commodities,
        extraction.regions,
        gfw_overrides=gfw_overrides if gfw_overrides else None,
        forest500_score=forest500_score,
    )
    risk_level = get_risk_level(risk_score)

    # Compute confidence score
    sources_responded = sum(1 for s in [csr_result, trase_result, forest500_result, gfw_result]
                           if isinstance(s, dict) and s.get("status") == "success")
    confidence_score = compute_confidence_score(
        num_sources_responded=sources_responded,
        has_commodities=bool(extraction.commodities),
        has_regions=bool(extraction.regions),
        has_csr=isinstance(csr_result, dict) and csr_result.get("status") == "success",
        has_forest500=isinstance(forest500_result, dict) and forest500_result.get("status") == "success",
        has_gfw=isinstance(gfw_result, dict) and gfw_result.get("status") == "success",
        has_trase=isinstance(trase_result, dict) and trase_result.get("status") == "success",
    )
    confidence_level = get_confidence_level(confidence_score)

    # Build disclosure flags
    flags = DisclosureFlags(
        no_csr_page_found=not (isinstance(csr_result, dict) and csr_result.get("status") == "success"),
        no_trase_data=not (isinstance(trase_result, dict) and trase_result.get("status") == "success"),
        no_forest500_data=not (isinstance(forest500_result, dict) and forest500_result.get("status") == "success"),
        no_gfw_data=not (isinstance(gfw_result, dict) and gfw_result.get("status") == "success"),
        low_confidence=confidence_score < 30,
        no_commodities_detected=not extraction.commodities,
        no_regions_detected=not extraction.regions,
    )

    # Generate summary
    summary = generate_summary(
        company, risk_score, risk_level, confidence_level,
        extraction.commodities, extraction.regions,
    )

    # Build response
    return RiskResponse(
        company=company,
        risk_score=risk_score,
        risk_level=risk_level,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        commodities=[CommodityDetail(**c) for c in extraction.commodities],
        regions=[RegionDetail(**r) for r in extraction.regions],
        breakdown=[CommodityRegionBreakdown(**b) for b in breakdown],
        sources=[
            _to_source_result(csr_result),
            _to_source_result(trase_result),
            _to_source_result(forest500_result),
            _to_source_result(gfw_result),
        ],
        flags=flags,
        summary=summary,
    )


@router.get("/risk/{company}", response_model=RiskResponse)
async def analyze_risk_get(company: str):
    """Convenience GET endpoint for risk analysis."""
    return await analyze_risk(RiskRequest(company=company))


# ---- Internal helpers ----

async def _get_csr_data(company: str) -> dict:
    """Fetch and process CSR page data."""
    try:
        result = await scraper.scrape(company)
        if result["status"] == "success":
            return {
                "source_name": "csr",
                "status": "success",
                "commodities_found": [],
                "regions_found": [],
                "raw_data": {
                    "url": result.get("url"),
                    "text_length": result.get("text_length", 0),
                    "text_preview": result.get("text", "")[:500],
                },
                "_text": result.get("text", ""),
            }
        return {
            "source_name": "csr",
            "status": "not_found",
            "commodities_found": [],
            "regions_found": [],
            "raw_data": {"urls_tried": result.get("urls_tried", 0)},
        }
    except Exception as e:
        return _error_source("csr", str(e))


async def _get_trase_data(company: str) -> dict:
    """Fetch and process Trase data."""
    try:
        result = trase_service.search(company)
        if result["status"] == "found":
            return {
                "source_name": "trase",
                "status": "success",
                "commodities_found": result.get("commodities", []),
                "regions_found": result.get("regions", []),
                "raw_data": {
                    "matched_names": result.get("matched_names", []),
                    "total_records": result.get("total_records", 0),
                    "volumes": result.get("volumes", {}),
                    "deforestation_indicators": result.get("deforestation_indicators", {}),
                },
            }
        return {
            "source_name": "trase",
            "status": result.get("status", "not_found"),
            "commodities_found": [],
            "regions_found": [],
            "error": result.get("error"),
        }
    except Exception as e:
        return _error_source("trase", str(e))


async def _get_forest500_data(company: str) -> dict:
    """Fetch and process Forest 500 data."""
    try:
        result = forest500_service.search(company)
        if result["status"] == "found":
            return {
                "source_name": "forest500",
                "status": "success",
                "commodities_found": result.get("commodities", []),
                "regions_found": [],
                "raw_data": {
                    "matched_names": result.get("matched_names", []),
                    "policy_score": result.get("policy_score"),
                    "category_scores": result.get("category_scores", {}),
                    "metadata": result.get("metadata", {}),
                },
            }
        return {
            "source_name": "forest500",
            "status": result.get("status", "not_found"),
            "commodities_found": [],
            "regions_found": [],
            "error": result.get("error"),
        }
    except Exception as e:
        return _error_source("forest500", str(e))


def _aggregate_text(company: str, csr: dict, trase: dict, forest500: dict) -> str:
    """Combine all source data into a single text blob for entity extraction."""
    parts = [company]

    # CSR page text
    if isinstance(csr, dict) and csr.get("_text"):
        parts.append(csr["_text"])

    # Trase commodities and regions
    if isinstance(trase, dict) and trase.get("status") == "success":
        parts.extend(trase.get("commodities_found", []))
        parts.extend(trase.get("regions_found", []))

    # Forest 500 commodities
    if isinstance(forest500, dict) and forest500.get("status") == "success":
        parts.extend(forest500.get("commodities_found", []))

    return " ".join(parts)


def _error_source(name: str, error: str) -> dict:
    """Create an error source result."""
    return {
        "source_name": name,
        "status": "failed",
        "commodities_found": [],
        "regions_found": [],
        "error": error,
    }


def _to_source_result(data: dict) -> SourceResult:
    """Convert internal source dict to SourceResult model."""
    if not isinstance(data, dict):
        return SourceResult(source_name="unknown", status="failed", error="Invalid data")

    # Remove internal fields
    clean_data = {k: v for k, v in data.items() if not k.startswith("_")}

    return SourceResult(
        source_name=clean_data.get("source_name", "unknown"),
        status=clean_data.get("status", "failed"),
        commodities_found=clean_data.get("commodities_found", []),
        regions_found=clean_data.get("regions_found", []),
        raw_data=clean_data.get("raw_data"),
        error=clean_data.get("error"),
    )
