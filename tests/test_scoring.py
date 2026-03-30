import pytest
from app.utils.scoring import compute_risk_score, get_risk_level, compute_confidence_score, get_confidence_level

def test_compute_risk_score_no_data():
    score, breakdown = compute_risk_score([], [])
    assert score == 0.0
    assert breakdown == []

def test_compute_risk_score_palm_oil():
    commodities = [{"name": "Palm Oil", "risk_weight": 0.95, "matched_keywords": []}]
    regions = [{"name": "Indonesia", "iso_code": "IDN", "risk_tier": "critical", "base_risk": 0.93, "linked_commodities": [], "sourcing_confidence": "", "evidence_source": ""}]
    
    score, breakdown = compute_risk_score(commodities, regions)
    
    assert score > 0
    assert len(breakdown) == 1
    assert breakdown[0]["commodity"] == "Palm Oil"
    assert breakdown[0]["region"] == "Indonesia"
    assert "combined_score" in breakdown[0]

def test_get_risk_level():
    assert get_risk_level(95.0) == "critical"
    assert get_risk_level(80.0) == "high"
    assert get_risk_level(65.0) == "moderate"
    assert get_risk_level(40.0) == "low"
    assert get_risk_level(10.0) == "minimal"

def test_compute_confidence_score():
    score = compute_confidence_score(
        num_sources_responded=4,
        has_commodities=True,
        has_regions=True,
        has_csr=True,
        has_forest500=True,
        has_gfw=True,
        has_trase=True
    )
    assert score == 100.0

def test_get_confidence_level():
    assert get_confidence_level(95.0) == "high"
    assert get_confidence_level(70.0) == "moderate"
    assert get_confidence_level(40.0) == "low"
    assert get_confidence_level(10.0) == "very_low"
