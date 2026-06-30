"""SEC EDGAR data ingestion module for the PE Investment Platform.

Fetches 10-K and 10-Q filings via the SEC REST API, downloads the raw HTML/XML,
strips tags with BeautifulSoup, and persists clean text to the database.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date
from typing import Any

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from core.config import settings
from db.crud import create_filing
from db.models import Filing
from db.session import async_session_factory

logger = logging.getLogger(__name__)

# SEC requires a descriptive User-Agent with real contact info on every request.
# Configure it via SEC_USER_AGENT in your .env (e.g. "Acme PE Research jane@acme.com").
SEC_HEADERS = {"User-Agent": settings.sec_user_agent}
SEC_BASE_URL = "https://www.sec.gov"
SEC_DATA_URL = "https://data.sec.gov"

# Rate limit: max 10 requests per second
RATE_LIMIT_DELAY = 0.12  # seconds between requests (slightly > 0.1 to be safe)


async def _get_cik_for_ticker(ticker: str, client: httpx.AsyncClient) -> str | None:
    """Map a ticker symbol to a zero-padded 10-digit CIK via SEC company_tickers.json."""
    resp = await client.get(f"{SEC_BASE_URL}/files/company_tickers.json")
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    for item in data.values():
        if item.get("ticker", "").upper() == ticker.upper():
            return str(item["cik_str"]).zfill(10)
    return None


async def get_company_filings(ticker: str) -> list[dict]:
    """Fetch all 10-K and 10-Q filings for a given ticker from SEC EDGAR.

    Returns a list of dicts with keys:
        - filing_type: str ("10-K" or "10-Q")
        - filing_date: date
        - accession_number: str
        - url: str (direct URL to the primary document)
    """
    async with httpx.AsyncClient(
        headers=SEC_HEADERS, timeout=30, follow_redirects=True
    ) as client:
        cik = await _get_cik_for_ticker(ticker, client)
        if not cik:
            logger.warning("Could not resolve CIK for ticker %s", ticker)
            return []

        await asyncio.sleep(RATE_LIMIT_DELAY)

        submissions_url = f"{SEC_DATA_URL}/submissions/CIK{cik}.json"
        resp = await client.get(submissions_url)
        resp.raise_for_status()
        data = resp.json()

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        filings: list[dict] = []
        for i, form in enumerate(forms):
            if form not in ("10-K", "10-Q"):
                continue
            acc = accession_numbers[i]
            acc_no_dash = acc.replace("-", "")
            primary_doc = primary_docs[i]
            doc_url = (
                f"{SEC_BASE_URL}/Archives/edgar/data/"
                f"{int(cik)}/{acc_no_dash}/{primary_doc}"
            )
            filings.append(
                {
                    "filing_type": form,
                    "filing_date": date.fromisoformat(filing_dates[i]),
                    "accession_number": acc,
                    "url": doc_url,
                    "cik": cik,
                    "primary_document": primary_doc,
                }
            )

        return filings


async def download_filing(
    accession_number: str,
    url: str | None = None,
    cik: str | None = None,
    primary_document: str | None = None,
) -> str:
    """Download the raw filing HTML/XML from SEC EDGAR.

    Accepts either a direct ``url`` or enough metadata to construct one.
    Returns the raw text content.
    """
    if not url:
        if not cik or not primary_document:
            raise ValueError(
                "download_filing requires either 'url' or both 'cik' and 'primary_document'"
            )
        acc_no_dash = accession_number.replace("-", "")
        url = (
            f"{SEC_BASE_URL}/Archives/edgar/data/"
            f"{int(cik)}/{acc_no_dash}/{primary_document}"
        )

    async with httpx.AsyncClient(
        headers=SEC_HEADERS, timeout=60, follow_redirects=True
    ) as client:
        await asyncio.sleep(RATE_LIMIT_DELAY)
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


def parse_filing_to_text(filing_html: str) -> str:
    """Strip HTML/XML tags and normalize whitespace from raw SEC filing content.

    Returns clean plain text suitable for storage and NLP pipelines.
    """
    soup = BeautifulSoup(filing_html, "html.parser")

    # Remove script and style elements entirely
    for element in soup(["script", "style"]):
        element.decompose()

    # Extract text with line breaks to preserve paragraph structure
    text = soup.get_text(separator="\n")

    # Normalize whitespace: collapse multiple blank lines and strip each line
    lines = [line.strip() for line in text.splitlines()]
    clean_lines = [line for line in lines if line]

    return "\n".join(clean_lines)


async def _filing_exists(
    session, company_id: int, accession_number: str
) -> bool:
    """Check whether a filing already exists for this company + accession_number."""
    result = await session.execute(
        select(Filing).where(
            Filing.company_id == company_id,
            Filing.accession_number == accession_number,
        )
    )
    return result.scalar_one_or_none() is not None


async def ingest_ticker(ticker: str, company_id: int) -> int:
    """Orchestrate the full ingestion flow for a single ticker.

    1. Fetch all 10-K / 10-Q filings from SEC EDGAR.
    2. For each filing: download → parse → store via ``db.crud.create_filing``.
    3. Skip filings already present in the database (by accession_number).

    Returns the number of new filings inserted.
    """
    filings = await get_company_filings(ticker)
    if not filings:
        logger.warning("No 10-K/10-Q filings found for ticker %s", ticker)
        return 0

    inserted_count = 0

    async with async_session_factory() as session:
        for filing_info in filings:
            accession_number = filing_info["accession_number"]

            if await _filing_exists(session, company_id, accession_number):
                logger.info(
                    "Skipping existing filing %s for company_id %s",
                    accession_number,
                    company_id,
                )
                continue

            try:
                raw_html = await download_filing(
                    accession_number=accession_number,
                    url=filing_info.get("url"),
                    cik=filing_info.get("cik"),
                    primary_document=filing_info.get("primary_document"),
                )
            except Exception as exc:
                logger.warning(
                    "Failed to download filing %s: %s",
                    accession_number,
                    exc,
                )
                continue

            try:
                clean_text = parse_filing_to_text(raw_html)
            except Exception as exc:
                logger.warning(
                    "Failed to parse filing %s: %s",
                    accession_number,
                    exc,
                )
                continue

            try:
                await create_filing(
                    session=session,
                    company_id=company_id,
                    filing_type=filing_info["filing_type"],
                    filing_date=filing_info["filing_date"],
                    accession_number=accession_number,
                    raw_text=clean_text,
                )
                inserted_count += 1
                logger.info(
                    "Inserted %s filing %s (%s)",
                    filing_info["filing_type"],
                    accession_number,
                    filing_info["filing_date"],
                )
            except Exception as exc:
                logger.warning(
                    "Failed to store filing %s in DB: %s",
                    accession_number,
                    exc,
                )
                continue

    return inserted_count


async def _get_company_id_by_ticker(ticker: str) -> int | None:
    """Look up company_id from the companies table by ticker symbol."""
    async with async_session_factory() as session:
        from db.models import Company

        result = await session.execute(
            select(Company).where(Company.ticker == ticker.upper())
        )
        company = result.scalar_one_or_none()
        return company.id if company else None


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


async def main_async() -> None:
    """Async entry point for CLI execution."""
    parser = argparse.ArgumentParser(description="Ingest SEC EDGAR filings for a ticker.")
    parser.add_argument("--ticker", required=True, help="Ticker symbol (e.g., BILL)")
    args = parser.parse_args()

    _setup_logging()
    ticker = args.ticker.upper()

    company_id = await _get_company_id_by_ticker(ticker)
    if company_id is None:
        logger.error("Company with ticker %s not found in database.", ticker)
        raise SystemExit(1)

    logger.info("Starting ingestion for %s (company_id=%s)", ticker, company_id)
    count = await ingest_ticker(ticker, company_id)
    logger.info("Ingestion complete. Inserted %s new filing(s).", count)


if __name__ == "__main__":
    asyncio.run(main_async())
