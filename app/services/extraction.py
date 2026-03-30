"""
Entity Extraction Engine for Deforestation Risk Scorer.

Detects deforestation-linked commodities (15 categories) and high-risk regions
(40+ countries) from text using keyword matching, synonym resolution, and fuzzy matching.
"""

from difflib import get_close_matches
from typing import NamedTuple


# ---------------------------------------------------------------------------
# COMMODITY → TOP COMPANIES MAPPING
# This allows product category searches (e.g., "Palm Oil" returns category-level risk)
# ---------------------------------------------------------------------------

COMMODITY_TO_COMPANIES: dict[str, list[str]] = {
    "Palm Oil": [
        "Wilmar", "Cargill", "Golden Agri Resources", "Sime Darby", "IOI Group",
        "KLK Kepong", "Musim Mas", "Astra Agro Lestari", "PP London Sumatra",
    ],
    "Soy": [
        "Cargill", "Bunge", "Archer Daniels Midland", "Louis Dreyfus", "Glencore",
        "Cofco", "Amaggi", "Viterra", "COFCO",
    ],
    "Beef / Cattle": [
        "JBS", "Cargill", "Tyson", "Minerva", "Marfrig",
        "BRF", "JBS Foods", "Cattlemen's", "Rabo",
    ],
    "Cocoa": [
        "Cargill", "Barry Callebaut", "Mars", "Nestlé", "Hershey",
        "Lindt", "Ferrero", "Mondelez", "Olam",
    ],
    "Coffee": [
        "Nestlé", "Starbucks", "JDE Peet's", "Lavazza", "Illy",
        "Peet's Coffee", "Keurig Dr Pepper", "Starbucks", "Nespresso",
    ],
    "Rubber": [
        "Halcyon Agri", "KLK Kepong", "Sime Darby", "Thai Rubber",
        "Vietnam Rubber", "Sinochem", "GMG Global", "Halcyon",
    ],
    "Timber": [
        "Samko", "Sonae", "Weyerhaeuser", "PotlatchDeltic", "Noble Group",
        "Olam", "Sinochem", "Klopman", "Vanuatu",
    ],
    "Pulp & Paper": [
        "Asia Pulp & Paper", "Sinar Mas", "April Group", "SCG Paper",
        "Siam Cement", "Nippon Paper", "Lee & Man", "Hengyuan",
    ],
    "Leather": [
        "Hermès", "LVMH", "Kering", "Nike", "Adidas",
        "Puma", "Deckers", " Wolverine", "Crocs",
    ],
    "Sugarcane": [
        "Copersucar", "Raízen", "São Martinho", "Crescent", "Aurora",
        "Bunge", "Cargill", "Louis Dreyfus", "Itaú",
    ],
    "Maize / Corn": [
        "Cargill", "Bunge", "Archer Daniels Midland", "Syngenta", "Corteva",
        "Bayer", "Limagrain", "KWS", "Corteva",
    ],
    "Rice": [
        "Olam", "Ricetec", "KRBL", "Lundberg", "Tatian",
        "Khao", "Asia Golden Rice", "Herba", "Adani",
    ],
    "Shrimp / Aquaculture": [
        "Charoen Pokphand", "CP Food", "Aqua Star", "Mardio", "Seabird",
        "Blue Star", "Gfresh", "Vietnam Seafood", "CP",
    ],
    "Charcoal": [
        "Sukarne", "JBS", "Minerva", "Marfrig", "Anglo",
        "Culligan", "Weber", "Kingsford", "Fogo",
    ],
    "Mining Minerals": [
        "Freeport-McMoRan", "Vale", "Rio Tinto", "BHP", "Newmont",
        "Anglo American", "Glencore", "Gold Fields", "Newcrest",
    ],
 }


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


def get_commodity_by_name(name: str) -> CommodityDef | None:
    """Look up a commodity by name (case-insensitive)."""
    name_lower = name.lower()
    for c in COMMODITIES:
        if c.name.lower() == name_lower:
            return c
    return None


def is_commodity_query(query: str) -> bool:
    """Check if the query matches a known commodity name or keyword."""
    query_lower = query.lower()
    if query_lower in [c.name.lower() for c in COMMODITIES]:
        return True
    for c in COMMODITIES:
        if query_lower in [kw.lower() for kw in c.keywords]:
            return True
    return False


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
    regions: list[dict]      # List of {name, iso_code, risk_tier, base_risk, linked_commodities, sourcing_confidence, evidence_source}
    operational_regions: list[dict]  # Countries where company operates but does NOT source commodities from


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


def _region_to_dict(
    region: RegionDef,
    sourcing_confidence: str = "inferred",
    evidence_source: str = "Global commodity-risk model",
) -> dict:
    """Convert a RegionDef to a dictionary for API response."""
    return {
        "name": region.name,
        "iso_code": region.iso_code,
        "risk_tier": region.risk_tier,
        "base_risk": region.base_risk,
        "linked_commodities": region.linked_commodities,
        "sourcing_confidence": sourcing_confidence,
        "evidence_source": evidence_source,
    }


import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")

def _fallback_extract_entities(text: str) -> ExtractionResult:
    """Fallback keyword matcher if LLM fails or is unconfigured."""
    # Keyword-only fallback: all regions are 'inferred' since we can't distinguish context
    raw_regions = extract_regions(text)
    for r in raw_regions:
        r["sourcing_confidence"] = "inferred"
        r["evidence_source"] = "Keyword matching (no LLM context analysis)"
    return ExtractionResult(
        commodities=extract_commodities(text),
        regions=raw_regions,
        operational_regions=[],
    )


async def extract_entities(text: str) -> ExtractionResult:
    """
    Extract both commodities and regions from text using OpenRouter LLM.
    Falls back to basic keyword matching if API key is missing or call fails.

    The LLM is instructed to distinguish between:
      - sourcing_countries: where the company sources/procures raw materials FROM
      - operational_countries: where the company manufactures, sells, or has offices
    Only sourcing_countries are used for risk scoring.
    """
    if not text:
        return ExtractionResult(commodities=[], regions=[], operational_regions=[])

    if not OPENROUTER_API_KEY:
        print("WARNING: OPENROUTER_API_KEY not found. Falling back to simple keyword matching.")
        return _fallback_extract_entities(text)

    # Prepare allowed enums for the LLM prompt to prevent hallucination
    valid_commodities = [c.name for c in COMMODITIES]
    valid_regions = list({r.name for r in REGIONS})

    system_prompt = f"""You are a strict, highly accurate corporate supply-chain intelligence engine.
Your task: Read the provided corporate sustainability/CSR text and return a JSON object with THREE arrays:
  1. "commodities" — raw materials the company sources, buys, produces, or uses in their supply chain
  2. "sourcing_countries" — countries the company SOURCES or PROCURES raw materials FROM
  3. "operational_countries" — countries where the company has offices, factories, sales, or operations but does NOT source raw materials from

CRITICAL RULES:
1. SOURCING vs OPERATIONS distinction is the MOST IMPORTANT rule:
   - "We source cocoa from Ghana" → Ghana goes in sourcing_countries
   - "We operate in China" / "Our products are sold in India" → goes in operational_countries
   - "Our palm oil supply chain in Indonesia" → Indonesia goes in sourcing_countries
   - "We have 80,000 employees in Mexico" → Mexico goes in operational_countries
2. Look for SOURCING verbs: source, procure, buy, import, supply chain origin, farm, plantation, grow, harvest, smallholder
3. Look for OPERATIONS verbs: operate, sell, market, manufacture, office, factory, distribute, employee, headquarter
4. If a country is mentioned with a commodity in a sourcing context, it is a sourcing_country
5. If unclear, put it in operational_countries (conservative approach)
6. ONLY extract commodities IF the company states they source, buy, produce, or use them in supply chain
7. Do NOT extract commodities from casual mentions, image captions, or hypothetical examples
8. Do not hallucinate. Only pull what is explicitly verifiable in the text
9. Commodities MUST match this allowed list: {valid_commodities}
10. Countries MUST match this allowed list: {valid_regions}
11. Return ONLY raw JSON, no markdown, matching this EXACT schema:
{{"commodities": ["Cocoa", "Palm Oil"], "sourcing_countries": ["Ghana", "Indonesia"], "operational_countries": ["China", "India"]}}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Cap text length at 40,000 characters to prevent expensive token usage
    text_to_analyze = text[:40000]

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract supply chain entities from the following text:\\n\\n{text_to_analyze}"}
        ],
        "temperature": 0.0,
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                
                # Strip markdown blocks if the LLM hallucinated them despite instructions
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()

                try:
                    parsed = json.loads(content)
                    found_commodities_raw = parsed.get("commodities", [])
                    # Support both old and new format
                    found_sourcing_raw = parsed.get("sourcing_countries", parsed.get("regions", []))
                    found_operational_raw = parsed.get("operational_countries", [])
                except json.JSONDecodeError as e:
                    print(f"Error parsing LLM output: {e}. Output was: {content}")
                    return _fallback_extract_entities(text)

                # Re-map valid commodities
                final_commodities = []
                for fc_name in found_commodities_raw:
                    for c in COMMODITIES:
                        if c.name.lower() == str(fc_name).lower():
                            final_commodities.append({
                                "name": c.name,
                                "risk_weight": c.risk_weight,
                                "matched_keywords": [fc_name],
                            })
                            break

                # Re-map sourcing regions — these get "estimated" confidence from LLM
                final_sourcing = []
                for fr_name in found_sourcing_raw:
                    fr_lower = str(fr_name).lower()
                    region = None
                    if fr_lower in _REGION_LOOKUP:
                        region = _REGION_LOOKUP[fr_lower]
                    else:
                        for r in REGIONS:
                            if r.name.lower() == fr_lower:
                                region = r
                                break
                    if region:
                        final_sourcing.append(_region_to_dict(
                            region,
                            sourcing_confidence="estimated",
                            evidence_source="CSR page LLM extraction (sourcing context)",
                        ))

                # Re-map operational regions — stored but NOT scored
                final_operational = []
                for fr_name in found_operational_raw:
                    fr_lower = str(fr_name).lower()
                    region = None
                    if fr_lower in _REGION_LOOKUP:
                        region = _REGION_LOOKUP[fr_lower]
                    else:
                        for r in REGIONS:
                            if r.name.lower() == fr_lower:
                                region = r
                                break
                    if region:
                        final_operational.append(_region_to_dict(
                            region,
                            sourcing_confidence="operational_only",
                            evidence_source="CSR page LLM extraction (operations/market context)",
                        ))

                # Deduplicate by name
                unique_comms = {c["name"]: c for c in final_commodities}.values()
                unique_sourcing = {r["name"]: r for r in final_sourcing}.values()
                unique_operational = {r["name"]: r for r in final_operational}.values()

                return ExtractionResult(
                    commodities=list(unique_comms),
                    regions=list(unique_sourcing),
                    operational_regions=list(unique_operational),
                )

            else:
                print(f"OpenRouter API Error: {response.status_code} - {response.text}")
                return _fallback_extract_entities(text)

    except Exception as e:
        print(f"LLM Extraction encountered an exception: {e}")
        return _fallback_extract_entities(text)


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
