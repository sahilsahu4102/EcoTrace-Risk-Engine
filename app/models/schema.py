"""
Pydantic models for the Deforestation Risk Scorer API.
"""

from pydantic import BaseModel, Field
from typing import Optional


class RiskRequest(BaseModel):
    """Input request for risk analysis."""
    company: str = Field(..., description="Company name to analyze", min_length=1, max_length=200)


class CommodityDetail(BaseModel):
    """Detail for a single detected commodity."""
    name: str = Field(..., description="Commodity name (e.g., 'Palm Oil')")
    risk_weight: float = Field(..., description="Inherent deforestation risk weight (0-1)")
    matched_keywords: list[str] = Field(default_factory=list, description="Keywords that triggered this match")


class RegionDetail(BaseModel):
    """Detail for a single detected region."""
    name: str = Field(..., description="Region/country name")
    iso_code: str = Field(..., description="ISO 3166-1 alpha-3 code")
    risk_tier: str = Field(..., description="Risk tier: critical, high, moderate, lower")
    base_risk: float = Field(..., description="Base deforestation risk (0-1)")
    linked_commodities: list[str] = Field(default_factory=list, description="Commodities linked to deforestation in this region")


class CommodityRegionBreakdown(BaseModel):
    """Risk breakdown for a specific commodity-region pair."""
    commodity: str
    region: str
    region_iso: str
    commodity_weight: float
    region_risk: float
    combined_score: float = Field(..., description="commodity_weight × region_risk × 100")


class SourceResult(BaseModel):
    """Result from a single data source."""
    source_name: str = Field(..., description="Name of the data source (trase, forest500, gfw, csr)")
    status: str = Field(..., description="Status: success, partial, failed, not_configured")
    commodities_found: list[str] = Field(default_factory=list)
    regions_found: list[str] = Field(default_factory=list)
    raw_data: Optional[dict] = Field(default=None, description="Additional data from this source")
    error: Optional[str] = Field(default=None, description="Error message if source failed")


class DisclosureFlags(BaseModel):
    """Flags indicating quality/gaps in the risk assessment."""
    no_csr_page_found: bool = Field(default=True, description="Company CSR page not accessible")
    no_trase_data: bool = Field(default=True, description="Company not found in Trase datasets")
    no_forest500_data: bool = Field(default=True, description="Company not found in Forest 500")
    no_gfw_data: bool = Field(default=True, description="GFW tree cover loss data unavailable")
    low_confidence: bool = Field(default=False, description="Confidence score below 30")
    no_commodities_detected: bool = Field(default=False, description="No deforestation-linked commodities found")
    no_regions_detected: bool = Field(default=False, description="No high-risk regions found")


class RiskResponse(BaseModel):
    """Full risk analysis response."""
    company: str = Field(..., description="Company name analyzed")
    risk_score: float = Field(..., description="Overall deforestation risk score (0-100)")
    risk_level: str = Field(..., description="Risk level: critical, high, moderate, low, minimal")
    confidence_score: float = Field(..., description="Confidence in the assessment (0-100)")
    confidence_level: str = Field(..., description="Confidence level: high, moderate, low, very_low")

    commodities: list[CommodityDetail] = Field(default_factory=list, description="Detected commodities")
    regions: list[RegionDetail] = Field(default_factory=list, description="Detected regions")
    breakdown: list[CommodityRegionBreakdown] = Field(default_factory=list, description="Commodity × Region risk matrix")

    sources: list[SourceResult] = Field(default_factory=list, description="Per-source results")
    flags: DisclosureFlags = Field(default_factory=DisclosureFlags, description="Disclosure quality flags")

    summary: str = Field(default="", description="Human-readable risk summary")
