"""
Deforestation Risk Scorer - FastAPI Application
Aggregates real public data to compute deforestation risk scores for companies.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data services on startup."""
    from app.routes.risk import load_data_services
    print("[Startup] Loading data services...")
    load_data_services()
    print("[Startup] Data services ready.")
    yield
    print("[Shutdown] Cleaning up.")


app = FastAPI(
    title="Deforestation Risk Scorer",
    description="Aggregates real public data from Trase, Forest 500, GFW, and CSR pages to compute deforestation risk scores for supply chains.",
    version="0.3.0 — Phase 3",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
from app.routes.risk import router as risk_router
app.include_router(risk_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.routes.risk import trase_service, forest500_service, gfw_service, scraper

    return {
        "status": "healthy",
        "version": "0.3.0",
        "phase": 3,
        "services": {
            "extraction_engine": "ready",
            "scoring_engine": "ready",
            "trase": "loaded" if trase_service.is_loaded else "no_data",
            "forest500": "loaded" if forest500_service.is_loaded else "no_data",
            "gfw": "api_key_set" if gfw_service.has_api_key else "fallback_mode",
            "csr_scraper": "api_key_set" if scraper.has_api_key else "direct_mode",
        },
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Deforestation Risk Scorer",
        "description": "Supply chain deforestation risk analysis API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "POST /api/risk": "Analyze a company (body: {\"company\": \"Unilever\"})",
            "GET /api/risk/{company}": "Analyze a company (URL param)",
        },
    }
