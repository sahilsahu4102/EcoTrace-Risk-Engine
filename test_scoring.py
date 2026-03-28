"""Test Phase 2 data services."""
import asyncio

# Test GFW Service (fallback mode — no API key needed)
from app.services.gfw_service import GFWService

async def test_gfw():
    gs = GFWService()
    result = await gs.get_tree_loss("BRA")
    print(f"[GFW] Brazil — Status: {result['status']}, Risk: {result['normalized_risk']}, Source: {result['source']}")

    result2 = await gs.get_tree_loss("IDN")
    print(f"[GFW] Indonesia — Status: {result2['status']}, Risk: {result2['normalized_risk']}")

    multi = await gs.get_multi_country_risk(["BRA", "IDN", "MYS", "COD"])
    print(f"[GFW] Multi-country risks: {multi}")

asyncio.run(test_gfw())

# Test Trase Service (will report "not available" if no CSVs downloaded yet)
from app.services.trase_service import TraseService
ts = TraseService()
result = ts.search("Cargill")
print(f"\n[Trase] Cargill search — Status: {result['status']}")

# Test Forest 500 Service (will report "not available" if no CSV downloaded yet)
from app.services.forest500_service import Forest500Service
fs = Forest500Service()
result = fs.search("Unilever")
print(f"[Forest500] Unilever search — Status: {result['status']}")
