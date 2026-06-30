"""Data validation and integrity checker for the PE Investment Platform.

Run from the CLI::

    python validate_data.py

Or import and call ``validate_all()`` programmatically.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select

from db.models import Company, Filing, FilingChunk, Financial
from db.session import async_session_factory


async def validate_all() -> dict:
    """Run all data integrity checks and return a structured report.

    Checks performed:
    1. Every company has ≥1 filing **or** ≥1 financial row.
    2. Every filing has embeddings **or** at least raw_text.
    3. No ``None`` values in critical financial fields (revenue, ebitda,
       total_debt, cash) for any row.
    """
    async with async_session_factory() as session:
        # ── Raw counts ────────────────────────────────────────────────────────
        companies_count = await session.scalar(select(func.count(Company.id)))
        filings_count = await session.scalar(select(func.count(Filing.id)))
        chunks_count = await session.scalar(select(func.count(FilingChunk.id)))
        financials_count = await session.scalar(select(func.count(Financial.id)))

        # ── Check 1: companies have filings or financials ─────────────────────
        result = await session.execute(select(Company))
        companies = result.scalars().all()

        companies_without_data = 0
        for company in companies:
            has_filings = bool(await session.scalar(
                select(func.count(Filing.id)).where(Filing.company_id == company.id)
            ))
            has_financials = bool(await session.scalar(
                select(func.count(Financial.id)).where(Financial.company_id == company.id)
            ))
            if not has_filings and not has_financials:
                companies_without_data += 1

        companies_with_data = companies_count - companies_without_data
        if companies_without_data == 0:
            companies_check = {
                "name": "companies_have_data",
                "status": "pass",
                "message": f"{companies_with_data}/{companies_count} companies have filings or financials",
            }
        else:
            companies_check = {
                "name": "companies_have_data",
                "status": "fail",
                "message": f"{companies_without_data}/{companies_count} companies missing both filings and financials",
            }

        # ── Check 2: filings have embeddings or raw_text ──────────────────────
        filings_without_embedding_or_text = await session.scalar(
            select(func.count(Filing.id)).where(
                Filing.embedding.is_(None),
                Filing.raw_text.is_(None),
            )
        )
        filings_with_embedding_or_text = filings_count - filings_without_embedding_or_text
        if filings_without_embedding_or_text == 0:
            filings_check = {
                "name": "filings_have_embeddings_or_text",
                "status": "pass",
                "message": f"{filings_with_embedding_or_text}/{filings_count} filings have embeddings or raw_text",
            }
        else:
            filings_check = {
                "name": "filings_have_embeddings_or_text",
                "status": "fail",
                "message": (
                    f"{filings_without_embedding_or_text}/{filings_count} filings "
                    f"missing both embeddings and raw_text"
                ),
            }

        # ── Check 3: critical financial fields are complete ───────────────────
        # Check for any row where *any* of the critical fields is None
        critical_none_count = await session.scalar(
            select(func.count(Financial.id)).where(
                (Financial.revenue.is_(None))
                | (Financial.ebitda.is_(None))
                | (Financial.total_debt.is_(None))
                | (Financial.cash.is_(None))
            )
        )
        complete_financials = financials_count - critical_none_count
        if critical_none_count == 0:
            financials_check = {
                "name": "financials_complete",
                "status": "pass",
                "message": f"{complete_financials}/{financials_count} financial rows have all critical fields",
            }
        else:
            financials_check = {
                "name": "financials_complete",
                "status": "fail",
                "message": f"{critical_none_count}/{financials_count} financial rows missing critical fields",
            }

        checks = [companies_check, filings_check, financials_check]
        overall = "pass" if all(c["status"] == "pass" for c in checks) else "fail"

        report = {
            "companies": companies_count,
            "filings": filings_count,
            "chunks": chunks_count,
            "financials": financials_count,
            "checks": checks,
            "overall": overall,
        }

        return report


def _print_summary(report: dict) -> None:
    """Print a human-readable summary of the validation report."""
    c = report["companies"]
    f = report["filings"]
    ch = report["chunks"]
    fin = report["financials"]

    symbols = []
    for check in report["checks"]:
        sym = "✓" if check["status"] == "pass" else "✗"
        symbols.append(f"{sym} {check['message']}")

    print(f"✓ {c} companies | ✓ {f} filings | ✓ {ch} chunks | {symbols[0].split(' ', 1)[1]}")
    print(f"  {' | '.join(symbols[1:])}")
    print(f"\nOverall: {report['overall'].upper()}")


async def main() -> None:
    """CLI entry point."""
    report = await validate_all()
    _print_summary(report)


if __name__ == "__main__":
    asyncio.run(main())
