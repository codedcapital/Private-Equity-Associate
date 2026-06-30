"""Pipeline router — deal pipeline management and agent dispatch.

Endpoints:
    GET    /pipeline/health          — Health check
    GET    /pipeline/runs           — List recent pipeline runs
    POST   /pipeline/run            — Run full pipeline (direct)
    GET    /pipeline/resume/{run_id}— Resume a failed pipeline run
    POST   /agents/dummy/run        — Dispatch dummy agent via BackgroundTasks
    POST   /agents/{agent_name}/run  — Dispatch an agent run via Celery
    GET    /agents/runs/{run_id}/status — Combined Celery + AgentLog status
    GET    /agents/runs/{run_id}     — Full agent log entry
    GET    /agents/runs              — List recent agent runs

Future endpoints:
    GET    /pipeline               — List all deals in pipeline
    POST   /pipeline                — Create a new deal
    PATCH  /pipeline/{deal_id}     — Update deal stage / details
    DELETE /pipeline/{deal_id}     — Remove a deal
"""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from sqlalchemy import desc, func, select

from agents.orchestrator import run_full_pipeline
from agents.state import deal_state_to_json
from core.celery_app import celery_app
from core.run_tracker import RunTracker
from core.tasks import run_agent_task
from db.models import AgentLog, AgentStatus
from db.session import async_session_factory
from schemas.agent import (
    AgentLogList,
    AgentLogRead,
    AgentRunRequest,
    AgentRunResponse,
    AgentStatus as AgentStatusSchema,
    PipelineRunList,
    PipelineRunRead,
    PipelineRunRequest,
)

from schemas.deal import DealCreate, DealList, DealRead, DealUpdate
from schemas.company import CompanyRead
from schemas.financials import FinancialProfile

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
agents_router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/health")
async def health() -> dict:
    """Health check for the pipeline router."""
    return {"status": "ok"}


@router.get("/deals")
async def list_deals_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    stage: str | None = None,
) -> list[dict]:
    """List all deals in the pipeline with company and financial details."""
    from db.crud import list_deals
    from db.models import Company, Deal, Financial

    async with async_session_factory() as session:
        deals = await list_deals(session, skip=skip, limit=limit, stage=stage)

        results = []
        for deal in deals:
            company = await session.get(Company, deal.company_id)
            # Get latest financials
            fin_result = await session.execute(
                select(Financial)
                .where(Financial.company_id == deal.company_id)
                .order_by(Financial.report_date.desc())
                .limit(1)
            )
            fin = fin_result.scalar_one_or_none()

            results.append({
                "id": deal.id,
                "company_id": deal.company_id,
                "stage": deal.stage.value,
                "entry_ev": deal.entry_ev,
                "entry_ebitda": deal.entry_ebitda,
                "lbo_irr": deal.lbo_irr,
                "lbo_moic": deal.lbo_moic,
                "memo_id": deal.memo_id,
                "last_updated": deal.last_updated.isoformat() if deal.last_updated else None,
                "created_at": deal.created_at.isoformat() if deal.created_at else None,
                "company": CompanyRead.model_validate(company).model_dump(mode="json") if company else None,
                "financials": FinancialProfile(
                    revenue=fin.revenue,
                    ebitda=fin.ebitda,
                    ebitda_margin=fin.ebitda_margin,
                    revenue_growth=fin.revenue_growth,
                    net_debt=fin.net_debt,
                    net_debt_ebitda=fin.net_debt_ebitda,
                    fcf=fin.fcf,
                    fcf_yield=fin.fcf_yield,
                ).model_dump(mode="json") if fin else None,
            })

    return results


@router.get("/deals/{deal_id}")
async def get_deal_endpoint(deal_id: int) -> dict:
    """Get a specific deal by ID with company and financial details."""
    from db.crud import get_deal_by_id
    from db.models import Company, Financial

    async with async_session_factory() as session:
        deal = await get_deal_by_id(session, deal_id)
        if not deal:
            raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

        company = await session.get(Company, deal.company_id)
        # Get latest financials
        fin_result = await session.execute(
            select(Financial)
            .where(Financial.company_id == deal.company_id)
            .order_by(Financial.report_date.desc())
            .limit(1)
        )
        fin = fin_result.scalar_one_or_none()

    return {
        "id": deal.id,
        "company_id": deal.company_id,
        "stage": deal.stage.value,
        "entry_ev": deal.entry_ev,
        "entry_ebitda": deal.entry_ebitda,
        "lbo_irr": deal.lbo_irr,
        "lbo_moic": deal.lbo_moic,
        "memo_id": deal.memo_id,
        "last_updated": deal.last_updated.isoformat() if deal.last_updated else None,
        "created_at": deal.created_at.isoformat() if deal.created_at else None,
        "company": CompanyRead.model_validate(company).model_dump(mode="json") if company else None,
        "financials": FinancialProfile(
            revenue=fin.revenue,
            ebitda=fin.ebitda,
            ebitda_margin=fin.ebitda_margin,
            revenue_growth=fin.revenue_growth,
            net_debt=fin.net_debt,
            net_debt_ebitda=fin.net_debt_ebitda,
            fcf=fin.fcf,
            fcf_yield=fin.fcf_yield,
        ).model_dump(mode="json") if fin else None,
    }


@router.post("/deals", response_model=DealRead)
async def create_deal_endpoint(request: DealCreate) -> DealRead:
    """Create a new deal in the pipeline."""
    from db.crud import create_deal

    async with async_session_factory() as session:
        deal = await create_deal(
            session,
            company_id=request.company_id,
            stage=request.stage,
            entry_ev=request.entry_ev,
            entry_ebitda=request.entry_ebitda,
            lbo_irr=request.lbo_irr,
            lbo_moic=request.lbo_moic,
            memo_id=request.memo_id,
        )
    return DealRead.model_validate(deal)


@router.patch("/deals/{deal_id}", response_model=DealRead)
async def update_deal_endpoint(deal_id: int, request: DealUpdate) -> DealRead:
    """Update a deal's stage or financials."""
    from db.crud import update_deal

    async with async_session_factory() as session:
        updates = request.model_dump(exclude_unset=True)
        deal = await update_deal(session, deal_id, **updates)
        if not deal:
            raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    return DealRead.model_validate(deal)


@router.delete("/deals/{deal_id}")
async def delete_deal_endpoint(deal_id: int) -> dict:
    """Delete a deal from the pipeline."""
    from db.crud import delete_deal

    async with async_session_factory() as session:
        success = await delete_deal(session, deal_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    return {"deleted": True, "deal_id": deal_id}


@router.get("/runs", response_model=PipelineRunList)
async def list_pipeline_runs(
    limit: int = Query(50, ge=1, le=100),
) -> PipelineRunList:
    """List recent pipeline runs with aggregated duration and cost.

    Queries the ``agent_logs`` table, groups by ``run_id``, and returns
    a summary for each run including the company name (extracted from
    ``input_data`` when available).
    """
    async with async_session_factory() as session:
        stmt = (
            select(
                AgentLog.run_id,
                AgentLog.status,
                AgentLog.duration_ms,
                AgentLog.cost_usd,
                AgentLog.input_data,
            )
            .order_by(AgentLog.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.all()

    runs: list[PipelineRunRead] = []
    for row in rows:
        input_data = row.input_data or {}
        company_name = input_data.get("company_name")
        if not company_name and isinstance(input_data.get("company_id"), int):
            company_name = f"Company {input_data['company_id']}"
        runs.append(
            PipelineRunRead(
                run_id=row.run_id,
                company_name=company_name,
                status=row.status.value if row.status else "unknown",
                duration=row.duration_ms,
                cost_usd=row.cost_usd,
            )
        )

    return PipelineRunList(runs=runs)


# ── Full pipeline direct execution ───────────────────────────────────────────


@router.post("/run", response_model=AgentRunResponse)
async def run_pipeline(
    request: PipelineRunRequest,
    background_tasks: BackgroundTasks,
) -> AgentRunResponse:
    """Run the full deal pipeline end-to-end via BackgroundTasks.

    Creates an AgentLog entry, schedules the pipeline to run in the
    background, and returns the run_id immediately so the client can
    poll for status via /agents/runs/{run_id}/status.
    """
    tracker = RunTracker()
    run_id = await tracker.start_run(
        agent_name="full_pipeline",
        input_data=request.model_dump(),
    )
    await tracker.update_status(run_id=run_id, status=AgentStatus.RUNNING)

    async def _execute_pipeline() -> None:
        try:
            final_state = await run_full_pipeline(
                company_name_or_id=request.company_name_or_id,
                thesis=request.thesis,
                existing_run_id=run_id,
            )
            await tracker.update_status(
                run_id=run_id,
                status=AgentStatus.COMPLETE,
                output_data={"state_json": deal_state_to_json(final_state)},
            )
        except Exception as exc:
            await tracker.log_error(run_id, str(exc))

    background_tasks.add_task(_execute_pipeline)

    return AgentRunResponse(
        run_id=run_id,
        status=AgentStatusSchema.RUNNING,
        message="Pipeline started — poll /agents/runs/{run_id}/status for progress",
    )


@router.get("/resume/{run_id}", response_model=AgentRunResponse)
async def resume_pipeline(run_id: str) -> AgentRunResponse:
    """Resume a failed pipeline run from its last checkpoint.

    1. Validates the run exists and is in FAILED status.
    2. Loads the checkpointed state from agent_log output_data.
    3. Continues the pipeline from the next stage.
    """
    tracker = RunTracker()
    log = await tracker.get_run(run_id)
    if not log:
        raise HTTPException(status_code=404, detail="Run not found")
    if log.status != AgentStatus.FAILED:
        raise HTTPException(status_code=400, detail="Run is not in FAILED status")

    input_data = log.input_data or {}
    company_name_or_id = input_data.get("company_name_or_id") or input_data.get("company_id")
    if not company_name_or_id:
        raise HTTPException(status_code=400, detail="Missing company identifier in run input")

    try:
        await tracker.update_status(run_id=run_id, status=AgentStatus.RUNNING)
        final_state = await run_full_pipeline(
            company_name_or_id=company_name_or_id,
            thesis=input_data.get("thesis"),
            existing_run_id=run_id,
        )

        await tracker.update_status(
            run_id=run_id,
            status=AgentStatus.COMPLETE,
            output_data={"state_json": deal_state_to_json(final_state)},
        )

        return AgentRunResponse(
            run_id=run_id,
            status=AgentStatusSchema.COMPLETE,
            message="Pipeline resumed and completed successfully",
        )
    except Exception as exc:
        await tracker.log_error(run_id, str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


# ── Celery-based generic agent dispatch ──────────────────────────────────────


@agents_router.post("/{agent_name}/run")
async def run_agent(agent_name: str, request: AgentRunRequest) -> AgentRunResponse:
    """Dispatch an agent run via Celery.

    Supported agents: dummy, sourcing, research, competitive, financials, lbo, memo, full.

    1. Creates an AgentLog entry in PENDING state.
    2. Dispatches ``run_agent_task`` via Celery with ``task_id=run_id``.
    3. Returns the run_id so the client can poll for status.
    """
    tracker = RunTracker()
    run_id = await tracker.start_run(agent_name, request.model_dump())

    # Dispatch Celery task; task_id = run_id for easy status lookup
    run_agent_task.apply_async(
        args=[agent_name, request.model_dump(), run_id],
        task_id=run_id,
    )

    return AgentRunResponse(
        run_id=run_id,
        status=AgentStatusSchema.PENDING,
        message="Agent run dispatched",
    )


@agents_router.get("/runs/{run_id}/status")
async def get_run_status(run_id: str) -> dict:
    """Query combined Celery task status and AgentLog status."""
    # Celery side
    celery_result = celery_app.AsyncResult(run_id)
    celery_status = celery_result.status

    # DB side
    async with async_session_factory() as session:
        result = await session.execute(
            select(AgentLog).where(AgentLog.run_id == run_id)
        )
        log = result.scalar_one_or_none()

    if log is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "run_id": run_id,
        "celery_status": celery_status,
        "agent_status": log.status.value if log.status else None,
        "output_data": log.output_data,
        "errors": log.errors,
        "duration_ms": log.duration_ms,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@agents_router.get("/runs/{run_id}", response_model=AgentLogRead)
async def get_run(run_id: str) -> AgentLogRead:
    """Return the full agent log entry for a given run_id."""
    tracker = RunTracker()
    log = await tracker.get_run(run_id)
    if not log:
        raise HTTPException(status_code=404, detail="Run not found")
    return log


@agents_router.get("/runs", response_model=AgentLogList)
async def list_runs(
    agent_name: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
) -> AgentLogList:
    """List recent agent runs, optionally filtered by agent name."""
    tracker = RunTracker()
    logs = await tracker.list_runs(agent_name=agent_name, limit=limit)
    return AgentLogList(logs=logs, total=len(logs))
