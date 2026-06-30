"""Admin router — platform administration, agent logs, and system health.

Endpoints:
    GET    /admin/health          — Basic health check
    GET    /admin/ingest/status  — Ingestion pipeline status + DB counts
    POST   /admin/ingest/trigger — Trigger manual ingestion (background task)
    GET    /admin/validate       — Run data integrity validation
    GET    /admin/pipeline/status — Daily pipeline execution summary
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import func, select

from db.models import AgentLog, AgentStatus, Company, Filing, FilingChunk, Financial
from db.session import async_session_factory
from ingest.scheduler import _last_run_utc, run_nightly_ingestion
from schemas.agent import BulkIngestRequest, BulkIngestResponse, PipelineStatusRead
from validate_data import validate_all

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def health() -> dict:
    """Health check for the admin router."""
    return {"status": "ok"}


@router.get("/ingest/status")
async def ingest_status() -> dict:
    """Return the current ingestion pipeline status and DB counts."""
    async with async_session_factory() as session:
        companies = await session.scalar(select(func.count(Company.id)))
        filings = await session.scalar(select(func.count(Filing.id)))
        chunks = await session.scalar(select(func.count(FilingChunk.id)))
        financials = await session.scalar(select(func.count(Financial.id)))

    return {
        "last_run": _last_run_utc,
        "companies": companies,
        "filings": filings,
        "chunks": chunks,
        "financials": financials,
    }


@router.post("/ingest/trigger")
async def ingest_trigger(background_tasks: BackgroundTasks) -> dict:
    """Manually trigger the nightly ingestion pipeline in the background."""
    background_tasks.add_task(run_nightly_ingestion)
    return {"message": "Ingestion triggered in background", "status": "running"}


@router.post("/ingest/bulk", response_model=BulkIngestResponse)
async def ingest_bulk(request: BulkIngestRequest) -> BulkIngestResponse:
    """Bulk ingest new companies by ticker symbol.

    For each ticker:
      1. Look up or create the company via Yahoo Finance info.
      2. Run financial ingestion (and optionally SEC filings).

    Returns a per-ticker summary with created/existing/failed counts.
    """
    from ingest.run import run_bulk_ingestion

    # Deduplicate and clean tickers
    tickers = list(dict.fromkeys(t.strip().upper() for t in request.tickers if t.strip()))
    sources = request.sources or ["financials"]

    result = await run_bulk_ingestion(tickers, sources)
    return BulkIngestResponse(**result)


@router.get("/validate")
async def validate() -> dict:
    """Run all data integrity checks and return the structured report."""
    report = await validate_all()
    return report


@router.get("/pipeline/status", response_model=PipelineStatusRead)
async def pipeline_status() -> PipelineStatusRead:
    """Return daily pipeline execution summary.

    Aggregates agent_logs for the current UTC day to report active runs,
    completed runs, failed runs, and total cost and token usage.
    """
    today = datetime.utcnow().date()
    start_of_day = datetime(today.year, today.month, today.day, 0, 0, 0)
    end_of_day = start_of_day + timedelta(days=1)

    async with async_session_factory() as session:
        active_runs = await session.scalar(
            select(func.count(AgentLog.id)).where(
                AgentLog.status == AgentStatus.RUNNING,
                AgentLog.created_at >= start_of_day,
                AgentLog.created_at < end_of_day,
            )
        )

        completed_today = await session.scalar(
            select(func.count(AgentLog.id)).where(
                AgentLog.status == AgentStatus.COMPLETE,
                AgentLog.created_at >= start_of_day,
                AgentLog.created_at < end_of_day,
            )
        )

        failed_today = await session.scalar(
            select(func.count(AgentLog.id)).where(
                AgentLog.status == AgentStatus.FAILED,
                AgentLog.created_at >= start_of_day,
                AgentLog.created_at < end_of_day,
            )
        )

        total_cost = await session.scalar(
            select(func.coalesce(func.sum(AgentLog.cost_usd), 0.0)).where(
                AgentLog.created_at >= start_of_day,
                AgentLog.created_at < end_of_day,
            )
        )

        total_tokens = await session.scalar(
            select(func.coalesce(func.sum(AgentLog.tokens_used), 0)).where(
                AgentLog.created_at >= start_of_day,
                AgentLog.created_at < end_of_day,
            )
        )

    return PipelineStatusRead(
        active_runs=active_runs or 0,
        completed_today=completed_today or 0,
        failed_today=failed_today or 0,
        total_cost_today=round(float(total_cost or 0.0), 2),
        total_tokens_today=int(total_tokens or 0),
    )
