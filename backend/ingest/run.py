"""Unified ingestion runner.

Orchestrates multiple data pipelines (SEC filings, Yahoo Finance financials)
for a given ticker.
"""

import argparse
import asyncio
import logging

from sqlalchemy import select

from db.models import Company, CompanySource
from db.session import async_session_factory

logger = logging.getLogger(__name__)


async def _lookup_or_create_company(ticker: str) -> tuple[int, bool]:
    """Look up a company by ticker. If not found, create it via Yahoo Finance info.

    Returns (company_id, was_created).
    """
    import yfinance as yf

    async with async_session_factory() as session:
        result = await session.execute(
            select(Company).where(Company.ticker == ticker.upper())
        )
        company = result.scalar_one_or_none()
        if company:
            return company.id, False

    # Not found — fetch info from Yahoo Finance (run in thread to avoid blocking)
    try:
        def _fetch_info():
            t = yf.Ticker(ticker)
            return t.info

        info = await asyncio.to_thread(_fetch_info)
        name = info.get("longName") or info.get("shortName") or ticker.upper()
        sector = info.get("sector", "Unknown")
        industry = info.get("industry", "")
        combined_sector = f"{sector} / {industry}" if industry else sector

        async with async_session_factory() as session:
            from db.crud import create_company

            company = await create_company(
                session,
                name=name,
                ticker=ticker.upper(),
                sector=combined_sector,
                source=CompanySource.MANUAL,
            )
            return company.id, True
    except Exception as exc:
        logger.error("Failed to create company for ticker %s: %s", ticker, exc)
        raise ValueError(f"Could not create company for ticker {ticker}: {exc}")


async def _run_ingestion(ticker: str, sources: list[str], create_if_missing: bool = False) -> dict:
    """Run selected ingestion pipelines and return a summary.

    Args:
        ticker: Yahoo Finance ticker symbol.
        sources: List of ingestion sources ("sec", "financials", "all").
        create_if_missing: If True, create the company via Yahoo Finance if not found.
    """
    results: dict[str, str] = {}
    run_all = "all" in sources

    try:
        if create_if_missing:
            company_id, was_created = await _lookup_or_create_company(ticker)
            if was_created:
                results["company"] = "created"
            else:
                results["company"] = "existing"
        else:
            company_id, _ = await _lookup_or_create_company(ticker)
            results["company"] = "existing"
    except Exception as exc:
        logger.error("Failed to resolve company for ticker %s: %s", ticker, exc)
        results["error"] = str(exc)
        return results

    # Financials pipeline
    if run_all or "financials" in sources:
        from ingest.financial_loader import ingest_company_financials

        try:
            count = await ingest_company_financials(ticker)
            results["financials"] = f"{count} period(s) inserted"
        except Exception as exc:
            logger.error("Financials ingestion failed: %s", exc)
            results["financials"] = f"error: {exc}"

    # SEC pipeline
    if run_all or "sec" in sources:
        try:
            from ingest.sec_fetcher import ingest_ticker

            sec_result = await ingest_ticker(ticker, company_id)
            results["sec"] = f"{sec_result} filing(s) inserted"
        except ImportError:
            logger.warning("sec_fetcher module not found, skipping SEC ingestion")
            results["sec"] = "skipped (module not found)"
        except Exception as exc:
            logger.error("SEC ingestion failed: %s", exc)
            results["sec"] = f"error: {exc}"

    return results


async def run_bulk_ingestion(tickers: list[str], sources: list[str] = None) -> dict:
    """Bulk ingestion: create companies (if missing) and run ingestion for each ticker.

    Args:
        tickers: List of ticker symbols to ingest.
        sources: List of ingestion sources. Defaults to ["financials"].

    Returns:
        Summary dict with per-ticker results and aggregate counts.
    """
    if sources is None:
        sources = ["financials"]

    total = len(tickers)
    created = 0
    existing = 0
    failed = 0
    results: dict[str, dict] = {}

    for ticker in tickers:
        ticker = ticker.upper().strip()
        try:
            res = await _run_ingestion(ticker, sources, create_if_missing=True)
            results[ticker] = res
            if res.get("company") == "created":
                created += 1
            elif res.get("company") == "existing":
                existing += 1
            if "error" in res:
                failed += 1
        except Exception as exc:
            logger.exception("Bulk ingestion failed for %s", ticker)
            results[ticker] = {"error": str(exc)}
            failed += 1

    return {
        "total": total,
        "created": created,
        "existing": existing,
        "failed": failed,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified data ingestion runner")
    parser.add_argument("--ticker", required=True, help="Company ticker symbol")
    parser.add_argument(
        "--source",
        default="all",
        help="Comma-separated ingestion sources: sec, financials, all",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    sources = [s.strip().lower() for s in args.source.split(",")]
    ticker = args.ticker.upper().strip()

    results = asyncio.run(_run_ingestion(ticker, sources))

    print(f"\n{'=' * 50}")
    print(f"Ingestion summary for {ticker}")
    print(f"{'=' * 50}")
    for source, result in results.items():
        print(f"  {source:15s} -> {result}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
