"""Quick test for the scoring engine."""
from app.utils.scoring import (
    compute_risk_score, get_risk_level,
    compute_confidence_score, get_confidence_level,
    generate_summary,
)

commodities = [
    {"name": "Palm Oil", "risk_weight": 0.95},
    {"name": "Soy", "risk_weight": 0.90},
]
regions = [
    {"name": "Indonesia", "iso_code": "IDN", "base_risk": 0.93},
    {"name": "Brazil", "iso_code": "BRA", "base_risk": 0.95},
]

score, breakdown = compute_risk_score(commodities, regions)
risk_level = get_risk_level(score)
conf = compute_confidence_score(2, True, True)
conf_level = get_confidence_level(conf)

print(f"Risk Score: {score}/100 ({risk_level})")
print(f"Confidence: {conf}/100 ({conf_level})")
print(f"Breakdown: {len(breakdown)} commodity x region pairs")
for b in breakdown:
    print(f"  {b['commodity']} x {b['region']}: {b['combined_score']}")

summary = generate_summary("TestCorp", score, risk_level, conf_level, commodities, regions)
print(f"\nSummary: {summary}")
