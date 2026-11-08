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
    pairs: list[tuple[str, str, str]] | None = None,
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
        pairs: Optional (commodity, region name, evidence) pairs to score instead of
            every commodity x every region. Company analyses pass them: until 2026-11
            the full cross-product scored pairs such as "Palm Oil x Chile", which no
            trade record or producer list supports. With no usable pair the score
            falls back to the commodity-only estimate below.

    Returns:
        Tuple of (risk_score, breakdown_list)
    """
    if pairs is not None:
        by_commodity = {c["name"]: c for c in commodities}
        by_region = {r["name"]: r for r in regions}
        selected = [
            (by_commodity[c], by_region[r], evidence)
            for c, r, evidence in pairs
            if c in by_commodity and r in by_region
        ]
        if not selected:
            return compute_risk_score(commodities, [] if commodities else regions,
                                      gfw_overrides, forest500_score)
        return _score_pairs(selected, gfw_overrides, forest500_score)

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

    # Cross-product scoring (commodity-category queries, whose regions are the
    # commodity's own producer countries, so every pair is plausible)
    return _score_pairs(
        [(c, r, None) for c in commodities for r in regions], gfw_overrides, forest500_score
    )


def _score_pairs(
    pairs: list[tuple[dict, dict, str | None]],
    gfw_overrides: dict[str, float] | None,
    forest500_score: float | None,
) -> tuple[float, list[dict]]:
    """Average commodity_weight x region_risk x 100 over the given pairs."""
    breakdown = []
    total_score = 0.0

    for commodity, region, evidence in pairs:
        r_iso = region["iso_code"]
        # Use GFW live data if available, otherwise use base_risk
        if gfw_overrides and r_iso in gfw_overrides:
            r_risk = gfw_overrides[r_iso]
        else:
            r_risk = region["base_risk"]

        combined = commodity["risk_weight"] * r_risk * 100
        row = {
            "commodity": commodity["name"],
            "region": region["name"],
            "region_iso": r_iso,
            "commodity_weight": commodity["risk_weight"],
            "region_risk": r_risk,
            "combined_score": round(combined, 1),
        }
        if evidence:
            row["evidence"] = evidence
        breakdown.append(row)
        total_score += combined

    score = total_score / len(pairs) if pairs else 0.0

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

    return min(round(score, 1), 95)  # Cap at 95 - 100% confidence is unrealistic


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
            # Count estimated vs inferred regions
            estimated = [r["name"] for r in regions if r.get("sourcing_confidence") == "estimated"]
            inferred = [r["name"] for r in regions if r.get("sourcing_confidence") == "inferred"]

            if estimated:
                parts.append(f"with estimated sourcing in {', '.join(estimated)}")
            if inferred:
                parts.append(f"and inferred potential sourcing in {', '.join(inferred)}")

            if not estimated and not inferred:
                # Fallback: regions without confidence field
                if len(region_names) == 1:
                    parts.append(f"with potential sourcing exposure in {region_names[0]}")
                else:
                    parts.append(f"with potential sourcing exposure in {', '.join(region_names[:-1])} and {region_names[-1]}")

    summary = " ".join(parts) + "."

    # Add methodology note
    summary += (
        " Sourcing exposure is estimated using Trase commodity trade records, "
        "CSR page AI analysis, Forest 500 policy assessments, and Global Forest Watch data."
    )

    if confidence_level in ("low", "very_low"):
        summary += (
            f" Note: Assessment confidence is {confidence_level} due to limited available data. "
            f"Results should be interpreted with caution."
        )

    return summary

