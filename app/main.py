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
    from app.services.cache_db import init_db
    
    print("[Startup] Loading data services...")
    load_data_services()
    print("[Startup] Initializing cache DB...")
    init_db()
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
        "http://localhost:3001",
        "http://localhost:5173",
    ],
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
from app.routes.risk import router as risk_router
from app.routes.history import router as history_router

app.include_router(risk_router)
app.include_router(history_router, prefix="/api", tags=["History"])

import time
from fastapi import Request
from fastapi.responses import JSONResponse

# Simple in-memory rate limiting
RATE_LIMIT_DURATION = 60 # seconds
RATE_LIMIT_REQUESTS = 20
ip_request_counts = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Only limit the risk API to prevent abuse of external APIs
    if "/api/risk" in request.url.path and request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        if client_ip not in ip_request_counts:
            ip_request_counts[client_ip] = []
            
        # Clean old requests
        ip_request_counts[client_ip] = [ts for ts in ip_request_counts[client_ip] if current_time - ts < RATE_LIMIT_DURATION]
        
        if len(ip_request_counts[client_ip]) >= RATE_LIMIT_REQUESTS:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})
            
        ip_request_counts[client_ip].append(current_time)

    response = await call_next(request)
    return response



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
