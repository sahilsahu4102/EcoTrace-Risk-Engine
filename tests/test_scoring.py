import pytest

from app.utils.scoring import compute_risk_score, get_risk_level, compute_confidence_score, get_confidence_level


def _commodity(name, weight):
    return {"name": name, "risk_weight": weight, "matched_keywords": []}


def _region(name, iso, base_risk):
    return {"name": name, "iso_code": iso, "risk_tier": "critical", "base_risk": base_risk,
            "linked_commodities": [], "sourcing_confidence": "", "evidence_source": ""}


def test_compute_risk_score_no_data():
    score, breakdown = compute_risk_score([], [])
    assert score == 0.0
    assert breakdown == []


def test_compute_risk_score_palm_oil():
    score, breakdown = compute_risk_score([_commodity("Palm Oil", 0.95)], [_region("Indonesia", "IDN", 0.93)])

    assert score == round(0.95 * 0.93 * 100, 1)
    assert len(breakdown) == 1
    assert breakdown[0]["commodity"] == "Palm Oil"
    assert breakdown[0]["region"] == "Indonesia"
    assert breakdown[0]["combined_score"] == score


def test_pairs_are_averaged_and_breakdown_sorted():
    commodities = [_commodity("Soy", 0.9), _commodity("Palm Oil", 0.95)]
    regions = [_region("Brazil", "BRA", 0.8)]

    score, breakdown = compute_risk_score(commodities, regions)

    assert score == 74.0  # (72.0 + 76.0) / 2
    assert [b["commodity"] for b in breakdown] == ["Palm Oil", "Soy"]


def test_gfw_override_replaces_base_risk():
    score, breakdown = compute_risk_score([_commodity("Soy", 0.9)], [_region("Brazil", "BRA", 0.95)],
                                          gfw_overrides={"BRA": 0.5})
    assert score == 45.0
    assert breakdown[0]["region_risk"] == 0.5


def test_single_signal_is_half_weighted():
    assert compute_risk_score([_commodity("Soy", 0.9)], [])[0] == 45.0
    assert compute_risk_score([], [_region("Brazil", "BRA", 0.8)])[0] == 40.0


@pytest.mark.parametrize(
    "forest500_score, expected",
    [(None, 50.0), (0, 55.0), (20, 55.0), (21, 52.0), (60, 52.0), (61, 50.0), (79, 50.0), (80, 40.0), (100, 40.0)],
)
def test_forest500_policy_adjustment(forest500_score, expected):
    score, _ = compute_risk_score([_commodity("Soy", 0.5)], [_region("Brazil", "BRA", 1.0)],
                                  forest500_score=forest500_score)
    assert score == expected


def test_score_is_clamped_to_100():
    score, _ = compute_risk_score([_commodity("X", 1.0)], [_region("Brazil", "BRA", 0.98)], forest500_score=10)
    assert score == 100.0


def test_score_is_deterministic_and_order_independent():
    commodities = [_commodity("Soy", 0.9), _commodity("Cocoa", 0.8), _commodity("Coffee", 0.65)]
    regions = [_region("Brazil", "BRA", 0.95), _region("Ghana", "GHA", 0.78)]

    first = compute_risk_score(commodities, regions, forest500_score=50)
    assert compute_risk_score(commodities, regions, forest500_score=50) == first
    assert compute_risk_score(commodities[::-1], regions[::-1], forest500_score=50)[0] == first[0]


@pytest.mark.parametrize(
    "score, level",
    [(95.0, "critical"), (80.0, "critical"), (79.9, "high"), (60.0, "high"), (59.9, "moderate"),
     (40.0, "moderate"), (39.9, "low"), (20.0, "low"), (19.9, "minimal"), (0.0, "minimal")],
)
def test_get_risk_level(score, level):
    assert get_risk_level(score) == level


def test_compute_confidence_score_is_capped_at_95():
    score = compute_confidence_score(
        num_sources_responded=4,
        has_commodities=True,
        has_regions=True,
        has_csr=True,
        has_forest500=True,
        has_gfw=True,
        has_trase=True,
    )
    assert score == 95


def test_compute_confidence_score_partial():
    assert compute_confidence_score(num_sources_responded=1, has_commodities=True, has_regions=False,
                                    has_trase=True) == 35.0


@pytest.mark.parametrize(
    "score, level",
    [(95.0, "high"), (70.0, "high"), (69.9, "moderate"), (45.0, "moderate"), (44.9, "low"),
     (25.0, "low"), (24.9, "very_low"), (10.0, "very_low")],
)
def test_get_confidence_level(score, level):
    assert get_confidence_level(score) == level


def test_explicit_pairs_score_only_those_combinations():
    commodities = [_commodity("Soy", 0.9), _commodity("Palm Oil", 0.95)]
    regions = [_region("Brazil", "BRA", 0.8), _region("Indonesia", "IDN", 0.6)]
    pairs = [("Soy", "Brazil", "Trase trade records"), ("Palm Oil", "Indonesia", "producer")]

    score, breakdown = compute_risk_score(commodities, regions, pairs=pairs)

    assert score == round((0.9 * 0.8 + 0.95 * 0.6) / 2 * 100, 1)
    assert [(b["commodity"], b["region"], b["evidence"]) for b in breakdown] == [
        ("Soy", "Brazil", "Trase trade records"), ("Palm Oil", "Indonesia", "producer")]


def test_no_supported_pair_falls_back_to_the_commodity_only_estimate():
    commodities, regions = [_commodity("Soy", 0.9)], [_region("Chile", "CHL", 0.4)]
    assert compute_risk_score(commodities, regions, pairs=[]) == (45.0, [])  # 0.9 * 50
