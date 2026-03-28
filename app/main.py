"""
Deforestation Risk Scorer - FastAPI Application
Aggregates real public data to compute deforestation risk scores for companies.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="Deforestation Risk Scorer",
    description="Aggregates real public data from Trase, Forest 500, GFW, and CSR pages to compute deforestation risk scores for supply chains.",
    version="0.1.0 — Phase 1",
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "phase": 1,
        "services": {
            "extraction_engine": "ready",
            "scoring_engine": "ready",
            "trase": "not_configured",
            "forest500": "not_configured",
            "gfw": "not_configured",
            "csr_scraper": "not_configured",
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
    }
