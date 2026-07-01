"""FastAPI application entry-point for the AI-Driven PE Investment Platform.

Environment:
    ALLOWED_ORIGINS    Comma-separated CORS origins (default: * in dev)
    ENVIRONMENT        dev | prod | test (default: dev)
"""

import os
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.auth import get_current_user
from api.middleware import RequestLoggingMiddleware
from api.rate_limit import RateLimitMiddleware
from api.dependencies import get_db
from api.routers.opportunity_discovery import router as opportunity_discovery_router

from api.routers.admin import router as admin_router
from api.routers.companies import router as companies_router
from api.routers.competitive import router as competitive_router
from api.routers.dashboard import router as dashboard_router
from api.routers.financials import router as financials_router
from api.routers.intelligence import router as intelligence_router
from api.routers.lbo import router as lbo_router
from api.routers.market_pulse import router as market_pulse_router
from api.routers.memo import router as memo_router
from api.routers.overview import router as overview_router
from api.routers.pipeline import agents_router, router as pipeline_router
from api.routers.research import router as research_router
from api.routers.sourcing import router as sourcing_router

# ── Application factory ───────────────────────────────────────────────────────

ENV = os.getenv("ENVIRONMENT", "dev")
_origins = os.getenv("ALLOWED_ORIGINS", "")
if _origins:
    ALLOWED_ORIGINS = [o.strip() for o in _origins.split(",") if o.strip()]
else:
    ALLOWED_ORIGINS = ["*"] if ENV == "dev" else []

app = FastAPI(
    title="AI-Driven PE Investment Platform",
    description="FastAPI backend for AI-driven private equity deal sourcing, diligence, and pipeline management.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# ── Exception handlers ───────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return structured JSON for all unhandled exceptions.

    Never leaks raw tracebacks to the client in production.
    """
    error_id = getattr(request.state, "request_id", "unknown")
    traceback.print_exc()  # logged server-side

    if ENV == "dev":
        detail = f"{type(exc).__name__}: {exc}"
    else:
        detail = "Internal server error. Please contact support."

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": detail,
            "error_id": error_id,
        },
    )

# ── Router mounting ──────────────────────────────────────────────────────────

app.include_router(sourcing_router)
app.include_router(opportunity_discovery_router)
app.include_router(research_router)
app.include_router(financials_router)
app.include_router(lbo_router)
app.include_router(competitive_router)
app.include_router(memo_router)
app.include_router(pipeline_router)
app.include_router(agents_router)
app.include_router(intelligence_router)
app.include_router(admin_router)
app.include_router(companies_router)
app.include_router(market_pulse_router)
app.include_router(dashboard_router)
app.include_router(overview_router)

# ── Root health ──────────────────────────────────────────────────────────────

@app.get("/", tags=["root"])
async def root() -> dict:
    """Root endpoint — platform status."""
    return {"status": "ok", "service": "pe-platform", "version": "0.1.0"}
