"""Celery tasks for the PE Investment Platform.

All tasks that touch the database use a ``_run_async`` helper that works
both inside a running event loop (tests / eager mode) and in a plain
Celery worker thread (no event loop).
"""

import asyncio
import logging
import threading
import time

from celery import Task

from core.celery_app import celery_app
from core.run_tracker import RunTracker
from db.models import AgentStatus

logger = logging.getLogger(__name__)


# ── Async runner helper ──────────────────────────────────────────────────────

def _run_async(coro):
    """Run an async coroutine from a synchronous context.

    Handles two cases:
    1. **No event loop running** (real Celery worker) → uses ``asyncio.run()``.
    2. **Event loop already running** (tests / eager mode) → spawns a new
       thread, creates a fresh event loop there, and executes the coroutine.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No loop running – plain worker thread
        return asyncio.run(coro)

    # A loop is already running in this thread.  We cannot call
    # ``asyncio.run()`` or ``run_until_complete()`` on it, so we run the
    # coroutine in a dedicated background thread with its own loop.
    result_container = [None]
    exception_container = [None]

    def _target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_container[0] = loop.run_until_complete(coro)
        except Exception as exc:  # noqa: BLE001
            exception_container[0] = exc
        finally:
            loop.close()

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join()

    if exception_container[0] is not None:
        raise exception_container[0]
    return result_container[0]


# ── Placeholder agent registry ──────────────────────────────────────────────

class DummyAgent:
    """Placeholder agent that returns mock output."""

    async def run(self, input_data: dict) -> dict:
        return {
            "result": "dummy_output",
            "company_id": input_data.get("company_id"),
        }


class SourcingAgent:
    """Wrapper for the sourcing agent."""

    async def run(self, input_data: dict) -> dict:
        from agents.sourcing.graph import run_sourcing

        thesis = input_data.get("thesis", "")
        result = await run_sourcing(thesis)
        return dict(result)


class ResearchAgent:
    """Wrapper for the research agent."""

    async def run(self, input_data: dict) -> dict:
        from agents.research.graph import run_research

        company_id = input_data.get("company_id")
        if not company_id:
            raise ValueError("Missing company_id")
        result = await run_research(company_id)
        return dict(result)


class CompetitiveAgent:
    """Wrapper for the competitive agent."""

    async def run(self, input_data: dict) -> dict:
        from agents.competitive.graph import run_competitive

        company_id = input_data.get("company_id")
        if not company_id:
            raise ValueError("Missing company_id")
        result = await run_competitive(company_id)
        return dict(result)


class FinancialsAgent:
    """Wrapper for the financials agent."""

    async def run(self, input_data: dict) -> dict:
        from agents.financials.graph import run_financial_analysis

        company_id = input_data.get("company_id")
        if not company_id:
            raise ValueError("Missing company_id")
        result = await run_financial_analysis(company_id)
        return dict(result)


class LBOAgent:
    """Wrapper for the LBO agent."""

    async def run(self, input_data: dict) -> dict:
        from agents.lbo.graph import run_lbo_analysis

        company_id = input_data.get("company_id")
        if not company_id:
            raise ValueError("Missing company_id")
        overrides = input_data.get("overrides", {})
        result = await run_lbo_analysis(company_id, overrides=overrides)
        return dict(result)


class MemoAgent:
    """Wrapper for the memo agent."""

    async def run(self, input_data: dict) -> dict:
        from agents.memo.graph import run_memo_generation

        company_id = input_data.get("company_id")
        if not company_id:
            raise ValueError("Missing company_id")
        result = await run_memo_generation(company_id)
        return dict(result)


class FullPipelineAgent:
    """Wrapper for the full pipeline orchestrator."""

    async def run(self, input_data: dict) -> dict:
        from agents.orchestrator import run_full_pipeline

        company_name_or_id = input_data.get("company_name_or_id") or input_data.get("company_id")
        if not company_name_or_id:
            raise ValueError("Missing company_name_or_id")
        thesis = input_data.get("thesis")
        result = await run_full_pipeline(company_name_or_id, thesis=thesis)
        return dict(result)


AGENT_REGISTRY: dict[str, type | None] = {
    "dummy": DummyAgent,
    "sourcing": SourcingAgent,
    "research": ResearchAgent,
    "competitive": CompetitiveAgent,
    "financials": FinancialsAgent,
    "lbo": LBOAgent,
    "memo": MemoAgent,
    "full": FullPipelineAgent,
}


# ── Celery tasks ─────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3)
def run_agent_task(self: Task, agent_name: str, input_data: dict, run_id: str) -> dict:
    """Celery task that runs an agent and tracks status in AgentLog.

    Steps:
        1. Mark AgentLog as RUNNING.
        2. Look up the agent by name.
        3. Execute the agent.
        4. On success → mark COMPLETE, store output & duration.
        5. On failure  → mark FAILED, store error, retry with exponential backoff.
    """
    start_time = time.time()
    tracker = RunTracker()

    async def _execute() -> dict:
        # 1. Mark as RUNNING
        await tracker.update_status(run_id, AgentStatus.RUNNING)

        # 2. Look up agent
        agent_cls = AGENT_REGISTRY.get(agent_name)
        if agent_cls is None:
            raise ValueError(
                f"Agent '{agent_name}' is not registered or not implemented"
            )

        # 3. Run agent
        agent = agent_cls()
        output = await agent.run(input_data)

        # 4. Mark as COMPLETE
        duration_ms = int((time.time() - start_time) * 1000)
        await tracker.update_status(
            run_id,
            AgentStatus.COMPLETE,
            output_data=output,
            duration_ms=duration_ms,
        )
        return output

    try:
        result = _run_async(_execute())
        return {
            "run_id": run_id,
            "status": "complete",
            "output": result,
        }

    except Exception as exc:
        # 5. Mark as FAILED and retry with exponential backoff
        try:
            _run_async(tracker.log_error(run_id, str(exc)))
        except Exception as mark_err:  # noqa: BLE001
            logger.error(
                "Failed to persist FAILED status for run %s: %s", run_id, mark_err
            )

        retry_in = 2 ** self.request.retries
        logger.warning(
            "Agent task %s failed (attempt %d/%d), retrying in %ds: %s",
            run_id,
            self.request.retries + 1,
            self.max_retries,
            retry_in,
            exc,
        )
        raise self.retry(exc=exc, countdown=retry_in)


@celery_app.task
def run_nightly_ingestion_task() -> dict:
    """Celery beat wrapper for the nightly data ingestion pipeline."""
    from ingest.scheduler import run_nightly_ingestion

    return _run_async(run_nightly_ingestion())
