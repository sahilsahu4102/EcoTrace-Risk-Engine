from fastapi import APIRouter
from app.services.cache_db import get_recent_history

router = APIRouter()

@router.get("/history")
async def fetch_history():
    """Get the recent cached queries across the platform."""
    return {"history": get_recent_history(50)}
