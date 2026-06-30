"""Memo agent router — IC memo generation and management endpoints.

Endpoints:
    POST   /agents/memo/generate         — Generate an IC memo
    GET    /agents/memo/{memo_id}       — Retrieve a memo JSON + PDF URL
    GET    /agents/memo/{memo_id}/download — Download the PDF file
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from agents.memo.graph import run_memo_generation
from agents.memo.pdf_renderer import render_memo_pdf
from db.crud import get_ic_memo_by_id
from db.session import async_session_factory
from schemas.agent import AgentRunRequest, AgentRunResponse
from schemas.memo import ICMemoRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents/memo", tags=["memo"])


@router.get("/health")
async def health() -> dict:
    """Health check for the memo agent."""
    return {"status": "ok"}


@router.post("/generate", response_model=AgentRunResponse)
async def generate_memo(request: AgentRunRequest) -> AgentRunResponse:
    """Generate a new IC memo for the given company.

    Triggers the full LangGraph pipeline: aggregate_context → write_sections
    → edit_pass → format_output.  Persists the memo to the DB and returns
    the run identifier.
    """
    from agents.state import create_initial_state
    from core.run_tracker import RunTracker
    from db.models import AgentStatus

    tracker = RunTracker()
    run_id = await tracker.start_run(
        agent_name="MemoAgent",
        input_data={"company_id": request.company_id, "overrides": request.overrides},
    )

    try:
        await tracker.update_status(run_id, AgentStatus.RUNNING)
        final_state = await run_memo_generation(request.company_id)

        memo_id = final_state.get("memo_id")
        if memo_id is None:
            raise RuntimeError("Memo generation did not produce a memo_id")

        # Generate PDF
        company_name = final_state.get("company_name", "Unknown")
        memo_sections = final_state.get("memo_sections", {})
        pdf_path = await render_memo_pdf(memo_sections, company_name)

        # Update memo with PDF path
        async with async_session_factory() as session:
            from db.crud import update_ic_memo

            await update_ic_memo(session, memo_id, pdf_path=pdf_path)

        await tracker.update_status(
            run_id,
            AgentStatus.COMPLETE,
            output_data={"memo_id": memo_id, "pdf_path": pdf_path},
        )

        return AgentRunResponse(
            run_id=run_id,
            status=AgentStatus.COMPLETE,
            message=f"Memo generated successfully (memo_id={memo_id})",
        )
    except Exception as exc:
        logger.exception("Memo generation failed for company_id=%s", request.company_id)
        await tracker.log_error(run_id, str(exc))
        raise HTTPException(status_code=500, detail=f"Memo generation failed: {exc}")


@router.get("/{memo_id}")
async def get_memo(memo_id: int) -> dict[str, Any]:
    """Retrieve a memo by ID, returning JSON content and a PDF download URL."""
    async with async_session_factory() as session:
        memo = await get_ic_memo_by_id(session, memo_id)

    if not memo:
        raise HTTPException(status_code=404, detail=f"Memo with id={memo_id} not found")

    pdf_url = f"/agents/memo/{memo_id}/download" if memo.pdf_path else None

    return {
        "memo": ICMemoRead.model_validate(memo).model_dump(mode="json"),
        "pdf_download_url": pdf_url,
    }


@router.patch("/{memo_id}")
async def update_memo(memo_id: int, request: dict) -> dict[str, Any]:
    """Update memo sections manually (e.g. factual corrections).

    Accepts a JSON body with `{ "sections": { "section_id": "new content", ... } }`.
    Merges the provided sections into the existing memo sections.
    """
    from db.crud import get_ic_memo_by_id, update_ic_memo

    async with async_session_factory() as session:
        memo = await get_ic_memo_by_id(session, memo_id)
        if not memo:
            raise HTTPException(status_code=404, detail=f"Memo with id={memo_id} not found")

        new_sections = request.get("sections", {})
        existing = memo.sections or {}
        existing.update(new_sections)
        await update_ic_memo(session, memo_id, sections=existing)

    return {"memo_id": memo_id, "status": "updated", "sections_updated": list(new_sections.keys())}


@router.get("/{memo_id}/download")
async def download_memo_pdf(memo_id: int) -> FileResponse:
    """Download the generated PDF for a memo."""
    async with async_session_factory() as session:
        memo = await get_ic_memo_by_id(session, memo_id)

    if not memo:
        raise HTTPException(status_code=404, detail=f"Memo with id={memo_id} not found")

    if not memo.pdf_path or not os.path.exists(memo.pdf_path):
        raise HTTPException(status_code=404, detail="PDF not yet generated for this memo")

    return FileResponse(
        memo.pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(memo.pdf_path),
    )
