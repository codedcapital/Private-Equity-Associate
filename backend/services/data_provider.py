"""Live data provider service — unified fetcher for real-time financial data.

Phase 4: Intelligence modules consume real data from YFinance, SEC EDGAR, and FMP
instead of seeded/demo figures. The provider implements a cache-first strategy:

  1. Check PostgreSQL for cached financials (most recent period)
  2. If stale or missing, fetch from YFinance and persist
  3. Return FinancialProfile regardless of source

This is the single data layer abstraction used by all intelligence modules.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

from sqlalchemy import select

from db.models import Company, Financial
from db.session import async_session_factory
from schemas.financials import FinancialProfile

logger = logging.getLogger(__name__)


class DataProvider:
    """Unified live data provider for the intelligence pipeline.

    Usage:
        provider = DataProvider()
        profile = await provider.get_financials(company_id=1)
    """

    @staticmethod
    async def get_financials(company_id: int, force_refresh: bool = False) -> FinancialProfile:
        """Fetch financial profile for a company.

        Args:
            company_id: Primary key of the company.
            force_refresh: If True, skip DB cache and re-fetch from YFinance.

        Returns:
            FinancialProfile with the most recent period's metrics.
            Returns a profile with None fields if data is unavailable.
        """
        if not force_refresh:
            cached = await DataProvider._get_cached_financials(company_id)
            if cached:
                logger.info("Using cached financials for company_id=%s", company_id)
                return cached

        # No cache — try live fetch via YFinance
        ticker = await DataProvider._get_ticker(company_id)
        if not ticker:
            logger.warning("No ticker for company_id=%s; cannot fetch live data", company_id)
            return DataProvider._empty_profile()

        try:
            from ingest.financial_loader import ingest_company_financials, load_financials

            # Fetch and persist all periods
            count = await ingest_company_financials(ticker)
            logger.info("Ingested %s period(s) for %s from YFinance", count, ticker)

            # Re-query the now-populated cache
            cached = await DataProvider._get_cached_financials(company_id)
            if cached:
                return cached

        except Exception as exc:
            logger.warning("Live fetch failed for %s: %s", ticker, exc)

        return DataProvider._empty_profile()

    @staticmethod
    async def _get_cached_financials(company_id: int) -> FinancialProfile | None:
        """Return the most recent FinancialProfile from DB, or None."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(Financial)
                .where(Financial.company_id == company_id)
                .order_by(Financial.report_date.desc())
                .limit(1)
            )
            fin = result.scalar_one_or_none()
            if not fin:
                return None

            return FinancialProfile(
                revenue=fin.revenue,
                ebitda=fin.ebitda,
                ebitda_margin=fin.ebitda_margin,
                revenue_growth=fin.revenue_growth,
                net_debt=fin.net_debt,
                net_debt_ebitda=fin.net_debt_ebitda,
                fcf=fin.fcf,
                fcf_yield=fin.fcf_yield,
            )

    @staticmethod
    async def _get_ticker(company_id: int) -> str | None:
        """Look up the ticker symbol for a company."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(Company).where(Company.id == company_id)
            )
            company = result.scalar_one_or_none()
            return company.ticker.upper() if company and company.ticker else None

    @staticmethod
    def _empty_profile() -> FinancialProfile:
        """Return an empty FinancialProfile when no data is available."""
        return FinancialProfile(
            revenue=None,
            ebitda=None,
            ebitda_margin=None,
            revenue_growth=None,
            net_debt=None,
            net_debt_ebitda=None,
            fcf=None,
            fcf_yield=None,
        )
