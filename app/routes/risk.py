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
from app.services.extraction import (
    extract_entities,
    get_commodity_by_name,
    is_commodity_query,
    COMMODITY_TO_COMPANIES,
    COMMODITIES,
    REGIONS,
)
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


from app.services.cache_db import get_cached_risk, save_cached_risk

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

    # --- CACHE CHECK ---
    cached_data = get_cached_risk(company)
    if cached_data:
        return RiskResponse(**cached_data)
    # -------------------

    # Check if query is a commodity → return category-level risk
    if is_commodity_query(company):
        resp = await _analyze_commodity_category(company)
        save_cached_risk(
            company, resp.risk_score, resp.risk_level, 
            resp.confidence_score, resp.confidence_level, resp.model_dump()
        )
        return resp

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

    # Build extraction from REAL structured data (not text blobs)
    extraction = _merge_structured_extraction(csr_result, trase_result, forest500_result)

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
    resp = RiskResponse(
        company=company,
        risk_score=risk_score,
        risk_level=risk_level,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        commodities=[CommodityDetail(**c) for c in extraction.commodities],
        regions=[RegionDetail(**r) for r in extraction.regions],
        operational_regions=[RegionDetail(**r) for r in getattr(extraction, 'operational_regions', [])],
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

    save_cached_risk(
        company, resp.risk_score, resp.risk_level, 
        resp.confidence_score, resp.confidence_level, resp.model_dump()
    )

    return resp


@router.get("/risk/{company}", response_model=RiskResponse)
async def analyze_risk_get(company: str):
    """Convenience GET endpoint for risk analysis."""
    return await analyze_risk(RiskRequest(company=company))


async def _analyze_commodity_category(query: str) -> RiskResponse:
    """
    Analyze risk for a commodity category (product category search).
    
    Generates a Baseline Commodity Profile based on high-risk countries 
    known for producing this commodity, and fetches live GFW data.
    """
    commodity_def = get_commodity_by_name(query)
    if not commodity_def:
        return RiskResponse(
            company=query,
            risk_score=0.0,
            risk_level="unknown",
            confidence_score=0.0,
            confidence_level="very_low",
            commodities=[],
            regions=[],
            operational_regions=[],
            breakdown=[],
            sources=[],
            flags=DisclosureFlags(),
            summary=f"Unknown commodity: {query}",
        )

    commodity_name = commodity_def.name
    risk_weight = commodity_def.risk_weight

    commodity_detail = CommodityDetail(
        name=commodity_name,
        risk_weight=risk_weight,
        matched_keywords=commodity_def.keywords[:5],
    )

    linked_regions = [
        r for r in REGIONS
        if commodity_name in r.linked_commodities
    ]

    iso_codes = [r.iso_code for r in linked_regions]
    gfw_overrides = {}
    gfw_result = _error_source("gfw", "No regions detected")
    
    if iso_codes:
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

    regions_data = []
    for r in linked_regions:
        regions_data.append({
            "name": r.name,
            "iso_code": r.iso_code,
            "risk_tier": r.risk_tier,
            "base_risk": r.base_risk,
            "linked_commodities": r.linked_commodities,
            "sourcing_confidence": "inferred",
            "evidence_source": f"{commodity_name} is heavily sourced from this region globally",
        })

    risk_score, breakdown = compute_risk_score(
        commodities=[{
            "name": commodity_name,
            "risk_weight": risk_weight,
        }],
        regions=regions_data,
        gfw_overrides=gfw_overrides if gfw_overrides else None,
        forest500_score=None,
    )
    risk_level = get_risk_level(risk_score)

    sources_responded = 1 if gfw_result.get("status") == "success" else 0
    confidence_score = compute_confidence_score(
        num_sources_responded=sources_responded,
        has_commodities=True,
        has_regions=bool(linked_regions),
        has_gfw=gfw_result.get("status") == "success",
    )
    # Boost confidence manually since this is a baseline profile
    confidence_score = min(confidence_score + 15, 90)
    confidence_level = get_confidence_level(confidence_score)

    sources_list = [_to_source_result(gfw_result)] if gfw_result.get("status") == "success" else []

    if not linked_regions:
        summary = f"{commodity_name} is a {risk_weight*100:.0f}/100 risk commodity. No specific high-risk regions mapped."
    else:
        top_region = breakdown[0]["region"] if breakdown else "multiple regions"
        summary = (
            f"BASELINE COMMODITY PROFILE: {commodity_name} has an inherent deforestation risk "
            f"of {risk_score}/100. It is linked to deforestation in {len(linked_regions)} high-risk countries, "
            f"including {top_region}."
        )

    return RiskResponse(
        company=f"CATEGORY: {commodity_name}",
        risk_score=risk_score,
        risk_level=risk_level,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        commodities=[commodity_detail],
        regions=[RegionDetail(**r) for r in regions_data[:10]],
        operational_regions=[],
        breakdown=[CommodityRegionBreakdown(**b) for b in breakdown[:10]],
        sources=sources_list,
        flags=DisclosureFlags(
            no_commodities_detected=False,
            no_regions_detected=not linked_regions,
            no_gfw_data=gfw_result.get("status") != "success",
        ),
        summary=summary,
    )


async def _analyze_company_direct(company: str, skip_csr: bool = False) -> RiskResponse:
    """
    Internal function to analyze a company WITHOUT commodity detection.
    Used by category searches to analyze companies directly.
    """
    # Run all data sources concurrently (same as analyze_risk but without commodity check)
    if skip_csr:
        async def dummy_csr():
            return {
                "source_name": "csr",
                "status": "not_found",
                "commodities_found": [],
                "regions_found": [],
                "operational_regions_found": [],
                "error": "Skipped for category analysis to improve response time"
            }
        csr_task = asyncio.create_task(dummy_csr())
    else:
        csr_task = asyncio.create_task(_get_csr_data(company))

    trase_task = asyncio.create_task(_get_trase_data(company))
    forest500_task = asyncio.create_task(_get_forest500_data(company))

    csr_result, trase_result, forest500_result = await asyncio.gather(
        csr_task, trase_task, forest500_task,
        return_exceptions=True,
    )

    if isinstance(csr_result, Exception):
        csr_result = _error_source("csr", str(csr_result))
    if isinstance(trase_result, Exception):
        trase_result = _error_source("trase", str(trase_result))
    if isinstance(forest500_result, Exception):
        forest500_result = _error_source("forest500", str(forest500_result))

    extraction = _merge_structured_extraction(csr_result, trase_result, forest500_result)

    gfw_overrides = {}
    gfw_result = _error_source("gfw", "No regions detected")
    if extraction.regions:
        iso_codes = [r["iso_code"] for r in extraction.regions]
        try:
            gfw_overrides = await gfw_service.get_multi_country_risk(iso_codes)
        except Exception as e:
            gfw_result = _error_source("gfw", str(e))

    forest500_score = None
    if isinstance(forest500_result, dict) and forest500_result.get("status") == "success":
        raw = forest500_result.get("raw_data", {})
        forest500_score = raw.get("policy_score")

    risk_score, breakdown = compute_risk_score(
        extraction.commodities,
        extraction.regions,
        gfw_overrides=gfw_overrides if gfw_overrides else None,
        forest500_score=forest500_score,
    )
    risk_level = get_risk_level(risk_score)

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

    flags = DisclosureFlags(
        no_csr_page_found=not (isinstance(csr_result, dict) and csr_result.get("status") == "success"),
        no_trase_data=not (isinstance(trase_result, dict) and trase_result.get("status") == "success"),
        no_forest500_data=not (isinstance(forest500_result, dict) and forest500_result.get("status") == "success"),
        no_gfw_data=not (isinstance(gfw_result, dict) and gfw_result.get("status") == "success"),
        low_confidence=confidence_score < 30,
        no_commodities_detected=not extraction.commodities,
        no_regions_detected=not extraction.regions,
    )

    summary = generate_summary(company, risk_score, risk_level, confidence_level,
                           extraction.commodities, extraction.regions)

    return RiskResponse(
        company=company,
        risk_score=risk_score,
        risk_level=risk_level,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        commodities=[CommodityDetail(**c) for c in extraction.commodities],
        regions=[RegionDetail(**r) for r in extraction.regions],
        operational_regions=[RegionDetail(**r) for r in extraction.operational_regions] if hasattr(extraction, 'operational_regions') else [],
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


# ---- Internal helpers ----

async def _get_csr_data(company: str) -> dict:
    """Fetch and process CSR page data."""
    try:
        result = await scraper.scrape(company)
        if result["status"] == "success":
            # Extract entities explicitly from the website text
            text = result.get("text", "")
            from app.services.extraction import extract_entities
            extraction = await extract_entities(text)
            commodities = [c["name"] for c in extraction.commodities]
            sourcing_regions = [r["name"] for r in extraction.regions]
            operational_regions = [r["name"] for r in extraction.operational_regions]
            
            return {
                "source_name": "csr",
                "status": "success",
                "commodities_found": commodities,
                "regions_found": sourcing_regions,
                "operational_regions_found": operational_regions,
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
            "operational_regions_found": [],
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


def _merge_structured_extraction(csr: dict, trase: dict, forest500: dict):
    """
    Build extraction result from REAL structured data returned by each source.

    Priority order:
      1. CSR  — LLM-extracted commodities & SOURCING regions from the company's own website
      2. Trase — real trade-record commodities & sourcing countries from CSV data (HIGHEST confidence)
      3. Forest 500 — commodities from policy assessments

    Regions ONLY come from:
      - Trase (actual trade flows → 'confirmed' confidence)
      - CSR sourcing_countries (LLM-verified → 'estimated' confidence)
    Operational-only countries are stored separately and NOT used for risk scoring.
    """
    from app.services.extraction import (
        ExtractionResult, COMMODITIES, REGIONS, _REGION_LOOKUP, _region_to_dict,
        get_commodity_weight,
    )

    seen_commodities: dict[str, dict] = {}   # name -> detail dict
    seen_regions: dict[str, dict] = {}       # name -> detail dict
    seen_operational: dict[str, dict] = {}   # name -> detail dict (NOT scored)

    def _add_commodity(name: str, source: str):
        """Add a commodity if it maps to our known list."""
        if name in seen_commodities:
            return
        for c in COMMODITIES:
            if c.name.lower() == name.lower():
                seen_commodities[c.name] = {
                    "name": c.name,
                    "risk_weight": c.risk_weight,
                    "matched_keywords": [f"from_{source}"],
                }
                return

    def _add_region(name: str, confidence: str = "inferred", evidence: str = "Global commodity-risk model"):
        """Add a sourcing region if it maps to our known list."""
        name_lower = name.lower()
        region = None
        if name_lower in _REGION_LOOKUP:
            region = _REGION_LOOKUP[name_lower]
        else:
            for r in REGIONS:
                if r.name.lower() == name_lower:
                    region = r
                    break
        if region:
            # If region already exists, upgrade confidence if the new one is higher
            existing = seen_regions.get(region.name)
            confidence_rank = {"estimated": 2, "inferred": 1}  # All sourcing is probabilistic
            if existing:
                if confidence_rank.get(confidence, 0) > confidence_rank.get(existing.get("sourcing_confidence"), 0):
                    seen_regions[region.name] = _region_to_dict(region, confidence, evidence)
            else:
                seen_regions[region.name] = _region_to_dict(region, confidence, evidence)

    def _add_operational(name: str):
        """Add an operational-only region (NOT used for risk scoring)."""
        if name in seen_operational or name in seen_regions:
            return
        name_lower = name.lower()
        region = None
        if name_lower in _REGION_LOOKUP:
            region = _REGION_LOOKUP[name_lower]
        else:
            for r in REGIONS:
                if r.name.lower() == name_lower:
                    region = r
                    break
        if region:
            seen_operational[region.name] = _region_to_dict(
                region,
                sourcing_confidence="operational_only",
                evidence_source="Company operations/market presence (not sourcing)",
            )

    # --- Priority 1: CSR (company's own website, LLM-verified) ---
    if isinstance(csr, dict) and csr.get("status") == "success":
        for comm in csr.get("commodities_found", []):
            _add_commodity(comm, "csr")
        # Only sourcing regions go into risk scoring
        for reg in csr.get("regions_found", []):
            _add_region(reg, confidence="estimated", evidence="CSR page AI extraction (sourcing context)")
        # Operational regions stored separately
        for reg in csr.get("operational_regions_found", []):
            _add_operational(reg)

    # --- Priority 2: Trase (real trade records from CSV) ---
    if isinstance(trase, dict) and trase.get("status") == "success":
        for comm in trase.get("commodities_found", []):
            _add_commodity(comm, "trase")
        # Trase regions are REAL sourcing countries (estimated confidence - trade records prove sourcing activity)
        for reg in trase.get("regions_found", []):
            _add_region(reg, confidence="estimated", evidence="Trase supply chain trade records")

    # --- Priority 3: Forest 500 (policy assessment commodities) ---
    if isinstance(forest500, dict) and forest500.get("status") == "success":
        for comm in forest500.get("commodities_found", []):
            _add_commodity(comm, "forest500")

    # Remove operational regions that got promoted to sourcing
    for name in list(seen_operational.keys()):
        if name in seen_regions:
            del seen_operational[name]

    return ExtractionResult(
        commodities=list(seen_commodities.values()),
        regions=list(seen_regions.values()),
        operational_regions=list(seen_operational.values()),
    )


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
