import pytest
from app.services.extraction import (
    get_commodity_by_name,
    is_commodity_query,
    extract_entities,
)

def test_get_commodity_by_name():
    # Test valid matching
    commodity = get_commodity_by_name("Palm Oil")
    assert commodity is not None
    assert commodity.name == "Palm Oil"
    
    # Test case insensitivity
    commodity = get_commodity_by_name("pAlM oIl")
    assert commodity is not None
    
    # Test non-existent commodity
    assert get_commodity_by_name("Nonexistent Commodity") is None

def test_is_commodity_query():
    assert is_commodity_query("Palm Oil") is True
    assert is_commodity_query("Soybean") is True # matches keyword
    assert is_commodity_query("apple") is False

def test_extract_entities_empty():
    res = extract_entities("")
    assert res.commodities == []
    assert res.regions == []

def test_extract_entities_basic():
    text = "We source soy from Brazil and palm oil from Indonesia."
    res = extract_entities(text)
    
    commodity_names = [c["name"] for c in res.commodities]
    assert "Soy" in commodity_names
    assert "Palm Oil" in commodity_names
    
    region_isos = [r["iso_code"] for r in res.regions]
    assert "BRA" in region_isos
    assert "IDN" in region_isos
