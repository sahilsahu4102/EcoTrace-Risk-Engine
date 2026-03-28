"""
Entity Extraction Engine for Deforestation Risk Scorer.

Detects deforestation-linked commodities (15 categories) and high-risk regions
(40+ countries) from text using keyword matching, synonym resolution, and fuzzy matching.
"""

from difflib import get_close_matches
from typing import NamedTuple


# ---------------------------------------------------------------------------
# COMMODITY DEFINITIONS — 15 deforestation-linked commodities
# ---------------------------------------------------------------------------

class CommodityDef(NamedTuple):
    name: str
    risk_weight: float
    keywords: list[str]
    rationale: str


COMMODITIES: list[CommodityDef] = [
    CommodityDef(
        name="Palm Oil",
        risk_weight=0.95,
        keywords=[
            "palm oil", "palm kernel", "pko", "rspo", "oleochemical",
            "palm-based", "palm fat", "palm olein", "palm stearin",
            "palmitate", "palmate",
        ],
        rationale="#1 driver of tropical deforestation in SE Asia",
    ),
    CommodityDef(
        name="Soy",
        risk_weight=0.90,
        keywords=[
            "soy", "soya", "soybean", "soy bean", "soybean meal",
            "soy lecithin", "soy protein", "soy oil", "soja",
        ],
        rationale="Major driver in Amazon/Cerrado conversion",
    ),
    CommodityDef(
        name="Beef / Cattle",
        risk_weight=0.92,
        keywords=[
            "beef", "cattle", "bovine", "livestock", "tallow",
            "beef tallow", "cattle ranching", "hides", "bovine meat",
            "feedlot", "ranching",
        ],
        rationale="Largest single driver of Amazon deforestation",
    ),
    CommodityDef(
        name="Cocoa",
        risk_weight=0.80,
        keywords=[
            "cocoa", "cacao", "chocolate", "cocoa butter", "cocoa powder",
            "cocoa bean", "cocoa liquor", "cocoa mass",
        ],
        rationale="Driving forest loss in West Africa (Ghana, Côte d'Ivoire)",
    ),
    CommodityDef(
        name="Coffee",
        risk_weight=0.65,
        keywords=[
            "coffee", "arabica", "robusta", "green coffee", "coffee beans",
            "coffee cherry", "instant coffee",
        ],
        rationale="Shade-grown vs sun-grown; Vietnam, Brazil, Ethiopia",
    ),
    CommodityDef(
        name="Rubber",
        risk_weight=0.75,
        keywords=[
            "rubber", "natural rubber", "latex", "caoutchouc",
            "rubber plantation", "rubber wood",
        ],
        rationale="Expanding into forests in SE Asia & West Africa",
    ),
    CommodityDef(
        name="Timber",
        risk_weight=0.85,
        keywords=[
            "timber", "wood", "lumber", "logs", "hardwood", "softwood",
            "tropical timber", "logging", "sawmill", "plywood",
            "veneer", "teak", "mahogany", "meranti",
        ],
        rationale="Direct deforestation; legal and illegal logging",
    ),
    CommodityDef(
        name="Pulp & Paper",
        risk_weight=0.78,
        keywords=[
            "pulp", "paper", "cellulose", "wood pulp", "tissue",
            "paper products", "cardboard", "packaging paper",
            "dissolving pulp", "kraft paper",
        ],
        rationale="Industrial tree plantations replacing natural forests",
    ),
    CommodityDef(
        name="Leather",
        risk_weight=0.80,
        keywords=[
            "leather", "hides", "animal skin", "bovine leather",
            "rawhide", "tanning", "tannery",
        ],
        rationale="Linked to cattle ranching expansion",
    ),
    CommodityDef(
        name="Sugarcane",
        risk_weight=0.55,
        keywords=[
            "sugarcane", "sugar cane", "sugar", "ethanol", "biofuel",
            "cane sugar", "molasses", "bagasse",
        ],
        rationale="Indirect land-use change in Brazil",
    ),
    CommodityDef(
        name="Maize / Corn",
        risk_weight=0.45,
        keywords=[
            "maize", "corn", "animal feed", "feed crops", "corn starch",
            "corn oil", "silage",
        ],
        rationale="Indirect driver via feed crop expansion",
    ),
    CommodityDef(
        name="Rice",
        risk_weight=0.40,
        keywords=[
            "rice", "paddy", "rice cultivation", "rice paddy",
            "rice farming", "rice mill",
        ],
        rationale="Wetland/mangrove conversion in SE Asia",
    ),
    CommodityDef(
        name="Shrimp / Aquaculture",
        risk_weight=0.70,
        keywords=[
            "shrimp", "prawn", "aquaculture", "shrimp farming",
            "shrimp pond", "mariculture", "fish farming",
        ],
        rationale="Mangrove deforestation in Asia & Latin America",
    ),
    CommodityDef(
        name="Charcoal",
        risk_weight=0.82,
        keywords=[
            "charcoal", "wood charcoal", "charcoal production",
            "biomass charcoal", "lump charcoal",
        ],
        rationale="Major driver in Sub-Saharan Africa",
    ),
    CommodityDef(
        name="Mining Minerals",
        risk_weight=0.72,
        keywords=[
            "mining", "gold mining", "bauxite", "iron ore",
            "mining concession", "mineral extraction", "quarry",
            "tin mining", "copper mining", "nickel mining",
        ],
        rationale="Artisanal & industrial mining clears forests",
    ),
]


# ---------------------------------------------------------------------------
# REGION DEFINITIONS — 40+ countries grouped by risk tier
# ---------------------------------------------------------------------------

class RegionDef(NamedTuple):
    name: str
    iso_code: str
    base_risk: float
    risk_tier: str  # critical, high, moderate, lower
    linked_commodities: list[str]
    aliases: list[str]


REGIONS: list[RegionDef] = [
    # ---- CRITICAL (≥0.85) ----
    RegionDef("Brazil", "BRA", 0.95, "critical",
              ["Soy", "Beef / Cattle", "Coffee", "Timber", "Sugarcane"],
              ["brasil", "brazilian", "amazonia", "amazon"]),
    RegionDef("Indonesia", "IDN", 0.93, "critical",
              ["Palm Oil", "Rubber", "Pulp & Paper", "Timber"],
              ["indonesian"]),
    RegionDef("Democratic Republic of Congo", "COD", 0.90, "critical",
              ["Timber", "Charcoal", "Mining Minerals", "Cocoa"],
              ["dr congo", "drc", "congo-kinshasa", "congo kinshasa", "zaire"]),
    RegionDef("Malaysia", "MYS", 0.88, "critical",
              ["Palm Oil", "Rubber", "Timber"],
              ["malaysian"]),
    RegionDef("Paraguay", "PRY", 0.86, "critical",
              ["Soy", "Beef / Cattle", "Timber"],
              ["paraguayan"]),
    RegionDef("Bolivia", "BOL", 0.85, "critical",
              ["Soy", "Beef / Cattle", "Timber"],
              ["bolivian"]),

    # ---- HIGH (0.70–0.84) ----
    RegionDef("Côte d'Ivoire", "CIV", 0.83, "high",
              ["Cocoa", "Rubber", "Palm Oil"],
              ["ivory coast", "cote divoire", "cote d'ivoire", "cote d ivoire", "ivorian"]),
    RegionDef("Colombia", "COL", 0.82, "high",
              ["Beef / Cattle", "Cocoa", "Palm Oil", "Coffee"],
              ["colombian"]),
    RegionDef("Papua New Guinea", "PNG", 0.80, "high",
              ["Palm Oil", "Timber"],
              ["png", "papuan"]),
    RegionDef("Peru", "PER", 0.80, "high",
              ["Cocoa", "Coffee", "Palm Oil", "Mining Minerals"],
              ["peruvian"]),
    RegionDef("Myanmar", "MMR", 0.79, "high",
              ["Rubber", "Timber", "Palm Oil"],
              ["burma", "burmese", "myanmarese"]),
    RegionDef("Ghana", "GHA", 0.78, "high",
              ["Cocoa", "Timber", "Mining Minerals"],
              ["ghanaian"]),
    RegionDef("Cambodia", "KHM", 0.77, "high",
              ["Rubber", "Timber", "Sugarcane"],
              ["cambodian", "kampuchea"]),
    RegionDef("Laos", "LAO", 0.76, "high",
              ["Rubber", "Timber", "Maize / Corn"],
              ["lao pdr", "laotian"]),
    RegionDef("Argentina", "ARG", 0.75, "high",
              ["Soy", "Beef / Cattle", "Timber"],
              ["argentinian", "argentine"]),
    RegionDef("Nigeria", "NGA", 0.74, "high",
              ["Cocoa", "Palm Oil", "Timber", "Charcoal"],
              ["nigerian"]),
    RegionDef("Cameroon", "CMR", 0.73, "high",
              ["Cocoa", "Palm Oil", "Timber", "Rubber"],
              ["cameroonian"]),
    RegionDef("Ecuador", "ECU", 0.72, "high",
              ["Palm Oil", "Shrimp / Aquaculture", "Cocoa", "Timber"],
              ["ecuadorian"]),
    RegionDef("Honduras", "HND", 0.71, "high",
              ["Palm Oil", "Beef / Cattle", "Coffee"],
              ["honduran"]),
    RegionDef("Guatemala", "GTM", 0.70, "high",
              ["Palm Oil", "Beef / Cattle", "Sugarcane"],
              ["guatemalan"]),

    # ---- MODERATE (0.50–0.69) ----
    RegionDef("Madagascar", "MDG", 0.68, "moderate",
              ["Timber", "Mining Minerals", "Charcoal"],
              ["malagasy"]),
    RegionDef("Vietnam", "VNM", 0.65, "moderate",
              ["Coffee", "Rubber", "Shrimp / Aquaculture", "Rice"],
              ["vietnamese"]),
    RegionDef("Liberia", "LBR", 0.65, "moderate",
              ["Palm Oil", "Rubber", "Timber"],
              ["liberian"]),
    RegionDef("Republic of Congo", "COG", 0.63, "moderate",
              ["Timber", "Palm Oil"],
              ["congo-brazzaville", "congo brazzaville"]),
    RegionDef("Mexico", "MEX", 0.62, "moderate",
              ["Beef / Cattle", "Soy", "Palm Oil"],
              ["mexican"]),
    RegionDef("Sierra Leone", "SLE", 0.62, "moderate",
              ["Palm Oil", "Cocoa", "Mining Minerals"],
              ["sierra leonean"]),
    RegionDef("Central African Republic", "CAF", 0.60, "moderate",
              ["Timber", "Charcoal", "Mining Minerals"],
              ["car"]),
    RegionDef("Thailand", "THA", 0.60, "moderate",
              ["Rubber", "Palm Oil", "Maize / Corn", "Shrimp / Aquaculture"],
              ["thai"]),
    RegionDef("Tanzania", "TZA", 0.60, "moderate",
              ["Timber", "Charcoal"],
              ["tanzanian"]),
    RegionDef("India", "IND", 0.58, "moderate",
              ["Palm Oil", "Soy", "Coffee", "Rubber"],
              ["indian"]),
    RegionDef("Mozambique", "MOZ", 0.58, "moderate",
              ["Timber", "Charcoal", "Soy"],
              ["mozambican"]),
    RegionDef("Venezuela", "VEN", 0.55, "moderate",
              ["Beef / Cattle", "Mining Minerals", "Timber"],
              ["venezuelan"]),
    RegionDef("Philippines", "PHL", 0.55, "moderate",
              ["Palm Oil", "Mining Minerals"],
              ["filipino", "philippine"]),
    RegionDef("Guyana", "GUY", 0.52, "moderate",
              ["Mining Minerals", "Timber"],
              ["guyanese"]),
    RegionDef("Suriname", "SUR", 0.50, "moderate",
              ["Mining Minerals", "Timber"],
              ["surinamese"]),

    # ---- LOWER (0.30–0.49) ----
    RegionDef("China", "CHN", 0.40, "lower",
              ["Rubber", "Soy"],
              ["chinese", "prc"]),
    RegionDef("Chile", "CHL", 0.38, "lower",
              ["Timber", "Pulp & Paper"],
              ["chilean"]),
    RegionDef("Costa Rica", "CRI", 0.35, "lower",
              ["Palm Oil"],
              ["costa rican"]),
    RegionDef("Uruguay", "URY", 0.32, "lower",
              ["Soy", "Beef / Cattle", "Timber"],
              ["uruguayan"]),
    RegionDef("South Africa", "ZAF", 0.30, "lower",
              ["Timber"],
              ["south african"]),
]


# ---------------------------------------------------------------------------
# SUB-REGION → COUNTRY MAPPING
# ---------------------------------------------------------------------------

SUB_REGION_MAP: dict[str, str] = {
    # Brazil sub-regions
    "cerrado": "Brazil",
    "amazon": "Brazil",
    "amazonia": "Brazil",
    "mato grosso": "Brazil",
    "mato grosso do sul": "Brazil",
    "para": "Brazil",
    "rondonia": "Brazil",
    "maranhao": "Brazil",
    "tocantins": "Brazil",
    "bahia": "Brazil",
    "goias": "Brazil",
    "gran chaco": "Argentina",
    "chaco": "Argentina",
    # Indonesia sub-regions
    "borneo": "Indonesia",
    "kalimantan": "Indonesia",
    "sumatra": "Indonesia",
    "sumatera": "Indonesia",
    "sulawesi": "Indonesia",
    "papua": "Indonesia",
    # Malaysia sub-regions
    "sabah": "Malaysia",
    "sarawak": "Malaysia",
    # Paraguay sub-regions
    "eastern paraguay": "Paraguay",
    # Peru sub-regions
    "loreto": "Peru",
    "ucayali": "Peru",
    "madre de dios": "Peru",
    # DR Congo sub-regions
    "ituri": "Democratic Republic of Congo",
    "kivu": "Democratic Republic of Congo",
}


# ---------------------------------------------------------------------------
# EXTRACTION ENGINE
# ---------------------------------------------------------------------------

class ExtractionResult(NamedTuple):
    """Result of commodity and region extraction from text."""
    commodities: list[dict]  # List of {name, risk_weight, matched_keywords}
    regions: list[dict]      # List of {name, iso_code, risk_tier, base_risk, linked_commodities}


def _build_region_lookup() -> dict[str, RegionDef]:
    """Build a case-insensitive lookup from all region names and aliases."""
    lookup = {}
    for region in REGIONS:
        lookup[region.name.lower()] = region
        for alias in region.aliases:
            lookup[alias.lower()] = region
    return lookup


_REGION_LOOKUP = _build_region_lookup()
_ALL_REGION_NAMES = list(_REGION_LOOKUP.keys())


def extract_commodities(text: str) -> list[dict]:
    """
    Extract deforestation-linked commodities from text.

    Uses case-insensitive keyword matching with deduplication.
    Returns list of commodity details with matched keywords.
    """
    if not text:
        return []

    text_lower = text.lower()
    found: dict[str, dict] = {}

    for commodity in COMMODITIES:
        matched_keywords = []
        for keyword in commodity.keywords:
            if keyword.lower() in text_lower:
                matched_keywords.append(keyword)

        if matched_keywords:
            found[commodity.name] = {
                "name": commodity.name,
                "risk_weight": commodity.risk_weight,
                "matched_keywords": matched_keywords,
            }

    return list(found.values())


def extract_regions(text: str) -> list[dict]:
    """
    Extract deforestation risk regions from text.

    Uses: direct matching, alias matching, sub-region mapping, and fuzzy matching.
    Returns list of region details with deduplication.
    """
    if not text:
        return []

    text_lower = text.lower()
    found: dict[str, dict] = {}

    # 1. Direct and alias matching
    for key, region in _REGION_LOOKUP.items():
        if key in text_lower and region.name not in found:
            found[region.name] = _region_to_dict(region)

    # 2. Sub-region → country mapping
    for sub_region, country in SUB_REGION_MAP.items():
        if sub_region in text_lower and country not in found:
            # Find the parent country
            for region in REGIONS:
                if region.name == country:
                    found[region.name] = _region_to_dict(region)
                    break

    # 3. Fuzzy matching — extract individual words/bigrams and match
    words = text_lower.split()
    # Build bigrams for multi-word country names
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words) - 2)]

    candidates = words + bigrams + trigrams
    for candidate in candidates:
        if len(candidate) < 4:
            continue
        matches = get_close_matches(candidate, _ALL_REGION_NAMES, n=1, cutoff=0.85)
        if matches:
            region = _REGION_LOOKUP[matches[0]]
            if region.name not in found:
                found[region.name] = _region_to_dict(region)

    return list(found.values())


def _region_to_dict(region: RegionDef) -> dict:
    """Convert a RegionDef to a dictionary for API response."""
    return {
        "name": region.name,
        "iso_code": region.iso_code,
        "risk_tier": region.risk_tier,
        "base_risk": region.base_risk,
        "linked_commodities": region.linked_commodities,
    }


def extract_entities(text: str) -> ExtractionResult:
    """
    Extract both commodities and regions from text.

    Main entry point for the extraction engine.
    """
    return ExtractionResult(
        commodities=extract_commodities(text),
        regions=extract_regions(text),
    )


# ---------------------------------------------------------------------------
# LOOKUP HELPERS (used by scoring engine)
# ---------------------------------------------------------------------------

def get_commodity_weight(commodity_name: str) -> float:
    """Look up the risk weight for a commodity by name."""
    for c in COMMODITIES:
        if c.name.lower() == commodity_name.lower():
            return c.risk_weight
    return 0.5  # default moderate weight for unknown commodities


def get_region_risk(region_name: str) -> float:
    """Look up the base risk for a region by name."""
    for r in REGIONS:
        if r.name.lower() == region_name.lower():
            return r.base_risk
    return 0.5  # default moderate risk for unknown regions


def get_region_by_iso(iso_code: str) -> RegionDef | None:
    """Look up a region by its ISO code."""
    for r in REGIONS:
        if r.iso_code == iso_code.upper():
            return r
    return None
