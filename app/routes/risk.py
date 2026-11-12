"""
Risk Analysis API Route for Deforestation Risk Scorer.

The /api/risk endpoint orchestrates all data sources concurrently,
runs extraction and scoring, and returns a comprehensive risk assessment.
"""

import asyncio
from datetime import datetime, timezone

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


from app.services.cache_db import get_cached_entry, save_cached_risk

# Background refreshes in flight (lowercased query), and their tasks so they are not garbage-collected
_refreshing: set[str] = set()
_background_tasks: set[asyncio.Task] = set()


@router.post("/risk", response_model=RiskResponse)
async def analyze_risk(request: RiskRequest):
    """
    Analyze deforestation risk for a company or a commodity category.

    Company analyses query 4 data sources concurrently:
    1. CSR page (direct HTTP, then the Jina Reader for bot-protected sites)
    2. Trase supply chain trade records (preprocessed JSON)
    3. Forest 500 policy rankings (preprocessed JSON)
    4. Global Forest Watch tree cover loss and deforestation alerts (live API)

    A cached result is returned at once; if it is older than a day it is also
    recomputed in the background, so the next visitor gets fresh data without
    anyone waiting for the live sources.
    """
    company = request.company.strip()

    cached = get_cached_entry(company)
    if cached:
        data, fresh = cached
        if not fresh:
            _refresh_in_background(company)
        return RiskResponse(**data)

    resp = await _compute(company)
    _save(company, resp)
    return resp


@router.get("/risk/{company}", response_model=RiskResponse)
async def analyze_risk_get(company: str):
    """Convenience GET endpoint for risk analysis."""
    return await analyze_risk(RiskRequest(company=company))


async def _compute(query: str) -> RiskResponse:
    if is_commodity_query(query):
        return await _analyze_commodity_category(query)
    return await _analyze_company_direct(query)


def _save(query: str, resp: RiskResponse) -> None:
    save_cached_risk(query, resp.risk_score, resp.risk_level,
                     resp.confidence_score, resp.confidence_level, resp.model_dump())


def _refresh_in_background(query: str) -> None:
    key = query.lower()
    if key in _refreshing:
        return
    _refreshing.add(key)

    async def run():
        try:
            _save(query, await _compute(query))
        except Exception as e:  # a failed refresh keeps the old result
            print(f"[cache] background refresh failed for {query}: {e}")
        finally:
            _refreshing.discard(key)

    task = asyncio.create_task(run())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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

    gfw_overrides, gfw_result = await _gfw_source([r.iso_code for r in linked_regions])

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
        computed_at=_now(),
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
    # GFW needs countries. Trase's come from local data in milliseconds, long before the
    # CSR page and its LLM step finish, so GFW starts on them now and runs alongside CSR.
    gfw_task = asyncio.create_task(_prefetch_gfw(trase_task))

    csr_result, trase_result, forest500_result, gfw_prefetched = await asyncio.gather(
        csr_task, trase_task, forest500_task, gfw_task,
        return_exceptions=True,
    )

    if isinstance(csr_result, Exception):
        csr_result = _error_source("csr", str(csr_result))
    if isinstance(trase_result, Exception):
        trase_result = _error_source("trase", str(trase_result))
    if isinstance(forest500_result, Exception):
        forest500_result = _error_source("forest500", str(forest500_result))

    extraction = _merge_structured_extraction(csr_result, trase_result, forest500_result)
    pairs, paired_regions = _scoring_pairs(extraction, trase_result)
    # Show the countries that are scored; with no supported pair, show what was found
    regions = paired_regions if pairs else extraction.regions

    # Only countries the CSR page added are fetched now; the rest came with the prefetch
    gfw_overrides, gfw_result = await _gfw_source(
        [r["iso_code"] for r in regions],
        prefetched=gfw_prefetched if isinstance(gfw_prefetched, dict) else None,
    )

    forest500_score = None
    if isinstance(forest500_result, dict) and forest500_result.get("status") == "success":
        raw = forest500_result.get("raw_data", {})
        forest500_score = raw.get("policy_score")

    risk_score, breakdown = compute_risk_score(
        extraction.commodities,
        extraction.regions,
        gfw_overrides=gfw_overrides if gfw_overrides else None,
        forest500_score=forest500_score,
        pairs=pairs,
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
        no_regions_detected=not regions,
    )

    summary = generate_summary(company, risk_score, risk_level, confidence_level,
                           extraction.commodities, regions)

    return RiskResponse(
        company=company,
        computed_at=_now(),
        risk_score=risk_score,
        risk_level=risk_level,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        commodities=[CommodityDetail(**c) for c in extraction.commodities],
        regions=[RegionDetail(**r) for r in regions],
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
            pairs = result.get("pairs", [])
            return {
                "source_name": "trase",
                "status": "success",
                "commodities_found": result.get("commodities", []),
                "regions_found": result.get("regions", []),
                "pairs": pairs,
                "raw_data": {
                    "matched_names": result.get("matched_names", [])[:25],
                    "matched_entities": result.get("matched_entities", 0),
                    "trade_flows": [
                        {"commodity": c, "country": r.title(), "tonnes": t} for c, r, t in pairs[:10]
                    ],
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


def _scoring_pairs(extraction, trase: dict) -> tuple[list[tuple[str, str, str]], list[dict]]:
    """Commodity-country pairs the evidence supports, and the regions they use.

    A pair is scored when Trase records that commodity leaving that country for
    this company, or when the country is a known producer of the commodity (its
    REGIONS entry links them). Every other combination of the commodities and
    countries found, such as "Palm Oil x Chile", is left out: until 2026-11 all of
    them were scored.
    """
    from app.services.extraction import _REGION_LOOKUP

    commodities = {c["name"] for c in extraction.commodities}
    regions = {r["name"]: r for r in extraction.regions}
    pairs: dict[tuple[str, str], str] = {}

    if isinstance(trase, dict) and trase.get("status") == "success":
        for commodity, country, _tonnes in trase.get("pairs", []):
            region = _REGION_LOOKUP.get(str(country).lower())
            if region and commodity in commodities and region.name in regions:
                pairs[(commodity, region.name)] = "Trase trade records"

    for name, region in regions.items():
        for commodity in commodities:
            if commodity in region.get("linked_commodities", []):
                pairs.setdefault((commodity, name), f"{name} is a major {commodity} producer")

    used = {region for _, region in pairs}
    return (
        [(c, r, evidence) for (c, r), evidence in sorted(pairs.items())],
        [region for name, region in regions.items() if name in used],
    )


async def _prefetch_gfw(trase_task: asyncio.Task) -> dict[str, dict]:
    """GFW data for the countries in the company's Trase records, fetched while CSR runs."""
    from app.services.extraction import _REGION_LOOKUP

    trase = await trase_task
    if not (isinstance(trase, dict) and trase.get("status") == "success"):
        return {}
    isos = [region.iso_code for name in trase.get("regions_found", [])
            if (region := _REGION_LOOKUP.get(str(name).lower()))]
    return await gfw_service.get_countries(isos) if isos else {}


async def _gfw_source(iso_codes: list[str], prefetched: dict[str, dict] | None = None) -> tuple[dict[str, float], dict]:
    """GFW risk per country, plus a source result that says how much of it was live.

    The service answers from region_risk_fallback.json when the API fails, so a
    returned value alone does not mean GFW responded. Only live API data earns
    the source its "success" status and its confidence points; static estimates
    are reported as "fallback". Countries in `prefetched` (fetched while the
    other sources ran) are not requested again.
    """
    if not iso_codes:
        return {}, _error_source("gfw", "No regions detected")
    prefetched = prefetched or {}
    missing = [iso for iso in dict.fromkeys(iso_codes) if iso not in prefetched]
    try:
        fetched = await gfw_service.get_countries(missing) if missing else {}
    except Exception as e:
        return {}, _error_source("gfw", str(e))
    countries = {iso: prefetched[iso] for iso in dict.fromkeys(iso_codes) if iso in prefetched}
    countries.update(fetched)

    overrides = {iso: data.get("normalized_risk", 0.5) for iso, data in countries.items()}
    live = [iso for iso, data in countries.items() if data.get("status") == "live_api"]
    live_detail = {
        iso: {k: countries[iso].get(k) for k in (
            "trend_ratio", "recent_years", "recent_avg_loss_ha", "baseline_avg_loss_ha",
            "alerts_90d_ha", "latest_alert",
        )}
        for iso in live
    }
    if len(live) == len(countries):
        status = "success"
    elif live:
        status = "partial"
    else:
        status = "fallback"
    return overrides, {
        "source_name": "gfw",
        "status": status,
        "commodities_found": [],
        "regions_found": list(overrides),
        "raw_data": {"risk_by_country": overrides, "live_countries": live, "live": live_detail},
    }


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
