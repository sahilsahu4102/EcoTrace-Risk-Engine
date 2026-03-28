"""
Risk & Confidence Scoring Engine for Deforestation Risk Scorer.

Computes a 0-100 risk score from commodity weights × region risk,
and a 0-100 confidence score from data source quality signals.
"""

from app.services.extraction import get_commodity_weight, get_region_risk


# ---------------------------------------------------------------------------
# RISK ENGINE
# ---------------------------------------------------------------------------

def compute_risk_score(
    commodities: list[dict],
    regions: list[dict],
    gfw_overrides: dict[str, float] | None = None,
    forest500_score: float | None = None,
) -> tuple[float, list[dict]]:
    """
    Compute overall deforestation risk score (0-100).

    Algorithm:
    1. For each (commodity, region) pair, compute: commodity_weight × region_risk × 100
    2. Aggregate using weighted average across all pairs
    3. Apply Forest 500 policy adjustment
    4. Clamp to 0-100

    Args:
        commodities: List of detected commodities with risk_weight
        regions: List of detected regions with base_risk
        gfw_overrides: Optional dict of {iso_code: normalized_risk} from GFW live data
        forest500_score: Optional policy score from Forest 500 (0-100)

    Returns:
        Tuple of (risk_score, breakdown_list)
    """
    if not commodities and not regions:
        return 0.0, []

    # If only commodities found (no regions), use average commodity weight
    if commodities and not regions:
        avg_weight = sum(c["risk_weight"] for c in commodities) / len(commodities)
        score = avg_weight * 50  # Scale down since no region confirmation
        score = _apply_forest500_adjustment(score, forest500_score)
        return round(min(max(score, 0), 100), 1), []

    # If only regions found (no commodities), use average region risk
    if regions and not commodities:
        avg_risk = sum(r["base_risk"] for r in regions) / len(regions)
        score = avg_risk * 50  # Scale down since no commodity confirmation
        score = _apply_forest500_adjustment(score, forest500_score)
        return round(min(max(score, 0), 100), 1), []

    # Cross-product scoring
    breakdown = []
    total_score = 0.0
    pair_count = 0

    for commodity in commodities:
        c_name = commodity["name"]
        c_weight = commodity["risk_weight"]

        for region in regions:
            r_name = region["name"]
            r_iso = region["iso_code"]

            # Use GFW live data if available, otherwise use base_risk
            if gfw_overrides and r_iso in gfw_overrides:
                r_risk = gfw_overrides[r_iso]
            else:
                r_risk = region["base_risk"]

            combined = c_weight * r_risk * 100
            breakdown.append({
                "commodity": c_name,
                "region": r_name,
                "region_iso": r_iso,
                "commodity_weight": c_weight,
                "region_risk": r_risk,
                "combined_score": round(combined, 1),
            })

            total_score += combined
            pair_count += 1

    # Weighted average
    if pair_count > 0:
        score = total_score / pair_count
    else:
        score = 0.0

    # Apply Forest 500 policy adjustment
    score = _apply_forest500_adjustment(score, forest500_score)

    # Clamp to 0-100
    score = round(min(max(score, 0), 100), 1)

    # Sort breakdown by combined_score descending
    breakdown.sort(key=lambda x: x["combined_score"], reverse=True)

    return score, breakdown


def _apply_forest500_adjustment(score: float, forest500_score: float | None) -> float:
    """
    Adjust risk score based on Forest 500 policy score.

    - Score 0-20 (poor/no policy): +5 penalty
    - Score 20-60 (weak policy): +2 penalty
    - Score 60-80 (decent policy): no change
    - Score 80-100 (strong policy): -10 reduction
    """
    if forest500_score is None:
        return score

    if forest500_score <= 20:
        return score + 5
    elif forest500_score <= 60:
        return score + 2
    elif forest500_score >= 80:
        return score - 10
    return score


def get_risk_level(score: float) -> str:
    """Convert numeric risk score to risk level label."""
    if score >= 80:
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 40:
        return "moderate"
    elif score >= 20:
        return "low"
    return "minimal"


# ---------------------------------------------------------------------------
# CONFIDENCE ENGINE
# ---------------------------------------------------------------------------

def compute_confidence_score(
    num_sources_responded: int,
    has_commodities: bool,
    has_regions: bool,
    has_csr: bool = False,
    has_forest500: bool = False,
    has_gfw: bool = False,
    has_trase: bool = False,
) -> float:
    """
    Compute confidence score (0-100) for the risk assessment.

    Factors:
    - Number of data sources that returned data (up to 45 pts)
    - Whether commodities were detected (10 pts)
    - Whether regions were detected (10 pts)
    - Individual source availability bonuses (5-10 pts each)

    Returns:
        Confidence score 0-100
    """
    score = 0.0

    # Source count contribution (up to 45)
    score += min(num_sources_responded * 15, 45)

    # Entity detection
    score += 10 if has_commodities else 0
    score += 10 if has_regions else 0

    # Per-source bonuses
    score += 10 if has_forest500 else 0
    score += 10 if has_gfw else 0
    score += 10 if has_trase else 0
    score += 5 if has_csr else 0

    return min(round(score, 1), 100)


def get_confidence_level(score: float) -> str:
    """Convert numeric confidence score to confidence level label."""
    if score >= 70:
        return "high"
    elif score >= 45:
        return "moderate"
    elif score >= 25:
        return "low"
    return "very_low"


# ---------------------------------------------------------------------------
# SUMMARY GENERATOR
# ---------------------------------------------------------------------------

def generate_summary(
    company: str,
    risk_score: float,
    risk_level: str,
    confidence_level: str,
    commodities: list[dict],
    regions: list[dict],
) -> str:
    """Generate a human-readable summary of the risk assessment."""
    commodity_names = [c["name"] for c in commodities]
    region_names = [r["name"] for r in regions]

    if not commodity_names and not region_names:
        return (
            f"Insufficient data to assess deforestation risk for {company}. "
            f"No deforestation-linked commodities or high-risk sourcing regions were detected. "
            f"This may indicate limited public disclosure or that the company operates "
            f"outside of high-risk commodity supply chains."
        )

    parts = [f"{company} has a {risk_level} deforestation risk score of {risk_score}/100"]

    if commodity_names:
        if len(commodity_names) == 1:
            parts.append(f"linked to {commodity_names[0]}")
        else:
            parts.append(f"linked to {', '.join(commodity_names[:-1])} and {commodity_names[-1]}")

    if region_names:
        if len(region_names) == 1:
            parts.append(f"with sourcing exposure in {region_names[0]}")
        else:
            parts.append(f"with sourcing exposure in {', '.join(region_names[:-1])} and {region_names[-1]}")

    summary = " ".join(parts) + "."

    if confidence_level in ("low", "very_low"):
        summary += (
            f" Note: Assessment confidence is {confidence_level} due to limited available data. "
            f"Results should be interpreted with caution."
        )

    return summary
