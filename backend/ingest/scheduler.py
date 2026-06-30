"""Scheduled ingestion orchestrator.

Uses APScheduler to run nightly data ingestion for all tracked companies.
Run in the foreground with::

    python -m ingest.scheduler
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from db.models import Company
from db.session import async_session_factory

logger = logging.getLogger(__name__)

# ── Shared scheduler state ─────────────────────────────────────────────────

_scheduler: AsyncIOScheduler | None = None
_scheduler_thread: threading.Thread | None = None
_last_run_utc: str | None = None


# ── Ingestion logic ────────────────────────────────────────────────────────

async def run_nightly_ingestion() -> dict:
    """Run the full ingestion pipeline for every tracked company.

    Returns a summary dict mapping ticker -> result description.
    """
    global _last_run_utc

    logger.info("Starting nightly ingestion run")

    async with async_session_factory() as session:
        result = await session.execute(
            select(Company).where(Company.ticker.isnot(None))
        )
        companies = result.scalars().all()

    if not companies:
        logger.warning("No companies with tickers found; nothing to ingest.")
        return {}

    tickers = [c.ticker for c in companies if c.ticker]
    logger.info("Ingesting %d company(ies): %s", len(tickers), ", ".join(tickers))

    # Import here to avoid circular deps at module load time
    from ingest.run import _run_ingestion

    results: dict[str, dict] = {}
    for company in companies:
        ticker = company.ticker
        if not ticker:
            continue
        try:
            res = await _run_ingestion(ticker, sources=["all"])
            results[ticker] = res
            logger.info("Ingestion for %s complete: %s", ticker, res)
        except Exception as exc:
            logger.exception("Ingestion for %s failed", ticker)
            results[ticker] = {"error": str(exc)}

    _last_run_utc = datetime.now(timezone.utc).isoformat()
    logger.info("Nightly ingestion run finished at %s", _last_run_utc)
    return results


# ── Scheduler lifecycle ───────────────────────────────────────────────────

def start_scheduler() -> None:
    """Start the APScheduler in a background daemon thread.

    The thread spins up its own asyncio event loop so the scheduler can
    execute async coroutines without blocking the caller's loop.
    """
    global _scheduler, _scheduler_thread

    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        logger.warning("Scheduler is already running")
        return

    def _run_loop() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _init_scheduler() -> AsyncIOScheduler:
            sched = AsyncIOScheduler()
            sched.add_job(
                run_nightly_ingestion,
                trigger=CronTrigger(hour=3, minute=0),
                id="nightly_ingestion",
                name="Nightly data ingestion for all tracked companies",
                replace_existing=True,
            )
            sched.start()
            logger.info("Scheduler started — nightly job at 03:00 UTC")
            return sched

        try:
            global _scheduler
            _scheduler = loop.run_until_complete(_init_scheduler())
            loop.run_forever()
        finally:
            loop.close()
            logger.info("Scheduler event loop closed")

    _scheduler_thread = threading.Thread(target=_run_loop, daemon=True, name="SchedulerThread")
    _scheduler_thread.start()

    # Brief wait so the scheduler has time to initialise before returning
    time.sleep(0.5)


def shutdown_scheduler() -> None:
    """Gracefully shut down the background scheduler."""
    global _scheduler, _scheduler_thread

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None

    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        # Daemon threads die automatically when the main process exits,
        # but we give it a moment to clean up.
        _scheduler_thread.join(timeout=2.0)

    _scheduler_thread = None
    logger.info("Scheduler shut down")


# ── CLI ───────────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> None:
    """Run the scheduler in the foreground (blocking)."""
    _setup_logging()
    start_scheduler()

    print("Scheduler running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down scheduler...")
    finally:
        shutdown_scheduler()


if __name__ == "__main__":
    main()
