"""Yahoo Finance financial data ingestion module.

Fetches annual income statement, balance sheet, and cash flow data
via yfinance, maps to the Financial model, computes derived ratios,
and persists to the PostgreSQL database.
"""

import argparse
import asyncio
import logging
import math
from datetime import date

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.crud import create_financial, list_financials
from db.models import Company
from db.session import async_session_factory
from schemas.financials import FinancialProfile

logger = logging.getLogger(__name__)

# ── Field mappings ──────────────────────────────────────────────────────────

_INCOME_ROW_LABELS = {
    "revenue": "Total Revenue",
    "net_income": "Net Income",
    "ebitda": "EBITDA",
    "operating_income": "Operating Income",
    "depreciation": "Reconciled Depreciation",
}

_BALANCE_ROW_LABELS = {
    "total_debt": "Total Debt",
    "cash": "Cash And Cash Equivalents",
    "total_assets": "Total Assets",
    "total_equity": "Stockholders Equity",
}

_CASHFLOW_ROW_LABELS = {
    "operating_cf": "Operating Cash Flow",
    "capex": "Capital Expenditure",
}

_ALTERNATE_EQUITY_LABEL = "Total Stockholder Equity"


def handle_missing_data(raw_value) -> float | None:
    """Return a clean float or None if the value is missing / invalid.

    Treats NaN, None, and exact zero as missing data per ingestion policy.
    """
    if raw_value is None:
        return None
    if isinstance(raw_value, float):
        if math.isnan(raw_value) or math.isinf(raw_value):
            logger.warning("Missing data: NaN/Inf value encountered")
            return None
    try:
        val = float(raw_value)
        if val == 0:
            logger.warning("Missing data: zero value treated as None")
            return None
        return val
    except (TypeError, ValueError):
        logger.warning("Missing data: unconvertible value %r", raw_value)
        return None


def _get_period_value(df, row_label: str, period) -> float | None:
    """Safely extract a single period value from a yfinance DataFrame."""
    if df is None or df.empty or row_label not in df.index:
        return None
    val = df.loc[row_label].get(period)
    return handle_missing_data(val)


async def load_financials(ticker: str, company_id: int) -> FinancialProfile:
    """Fetch annual financials from Yahoo Finance and persist each period.

    Args:
        ticker: Yahoo Finance ticker symbol.
        company_id: Primary key of the company in the local DB.

    Returns:
        A FinancialProfile populated with the most recent period's metrics.
    """

    def _fetch():
        t = yf.Ticker(ticker)
        return t.income_stmt, t.balance_sheet, t.cash_flow

    try:
        income_stmt, balance_sheet, cash_flow = await asyncio.to_thread(_fetch)
    except Exception as exc:
        logger.error("Failed to fetch yfinance data for %s: %s", ticker, exc)
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

    if income_stmt is None or income_stmt.empty:
        logger.warning("No income statement data available for %s", ticker)
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

    # Use sorted periods (ascending) so YoY growth is easy to compute
    periods = sorted(income_stmt.columns)

    latest_profile = FinancialProfile(
        revenue=None,
        ebitda=None,
        ebitda_margin=None,
        revenue_growth=None,
        net_debt=None,
        net_debt_ebitda=None,
        fcf=None,
        fcf_yield=None,
    )

    prev_revenue: float | None = None

    async with async_session_factory() as session:
        for idx, period in enumerate(periods):
            report_date = date(period.year, period.month, period.day)

            # ── Raw values from yfinance ────────────────────────────────────
            revenue = _get_period_value(
                income_stmt, _INCOME_ROW_LABELS["revenue"], period
            )
            net_income = _get_period_value(
                income_stmt, _INCOME_ROW_LABELS["net_income"], period
            )
            ebitda_raw = _get_period_value(
                income_stmt, _INCOME_ROW_LABELS["ebitda"], period
            )

            operating_income = _get_period_value(
                income_stmt, _INCOME_ROW_LABELS["operating_income"], period
            )
            depreciation = _get_period_value(
                income_stmt, _INCOME_ROW_LABELS["depreciation"], period
            )

            # Compute EBITDA if not reported directly
            ebitda = ebitda_raw
            if ebitda is None and operating_income is not None and depreciation is not None:
                ebitda = operating_income + depreciation

            total_debt = _get_period_value(
                balance_sheet, _BALANCE_ROW_LABELS["total_debt"], period
            )
            cash = _get_period_value(
                balance_sheet, _BALANCE_ROW_LABELS["cash"], period
            )
            total_assets = _get_period_value(
                balance_sheet, _BALANCE_ROW_LABELS["total_assets"], period
            )

            # Try primary equity label, then fallback
            total_equity = _get_period_value(
                balance_sheet, _BALANCE_ROW_LABELS["total_equity"], period
            )
            if total_equity is None:
                total_equity = _get_period_value(
                    balance_sheet, _ALTERNATE_EQUITY_LABEL, period
                )

            operating_cf = _get_period_value(
                cash_flow, _CASHFLOW_ROW_LABELS["operating_cf"], period
            )
            capex = _get_period_value(
                cash_flow, _CASHFLOW_ROW_LABELS["capex"], period
            )

            # Capex stored as absolute value
            if capex is not None:
                capex = abs(capex)

            # ── Derived fields ──────────────────────────────────────────────
            net_debt = None
            if total_debt is not None and cash is not None:
                net_debt = total_debt - cash

            fcf = None
            if operating_cf is not None and capex is not None:
                fcf = operating_cf - capex

            ebitda_margin = None
            if ebitda is not None and revenue is not None and revenue != 0:
                ebitda_margin = ebitda / revenue

            net_debt_ebitda = None
            if net_debt is not None and ebitda is not None and ebitda != 0:
                net_debt_ebitda = net_debt / ebitda

            revenue_growth = None
            if idx > 0 and revenue is not None and prev_revenue is not None and prev_revenue != 0:
                revenue_growth = (revenue - prev_revenue) / prev_revenue

            fcf_yield = None
            if fcf is not None and revenue is not None and revenue != 0:
                fcf_yield = fcf / revenue

            # ── Persist to DB ─────────────────────────────────────────────
            try:
                await create_financial(
                    session=session,
                    company_id=company_id,
                    report_date=report_date,
                    revenue=revenue,
                    ebitda=ebitda,
                    net_income=net_income,
                    total_debt=total_debt,
                    cash=cash,
                    total_assets=total_assets,
                    total_equity=total_equity,
                    operating_cf=operating_cf,
                    capex=capex,
                    net_debt=net_debt,
                    fcf=fcf,
                    ebitda_margin=ebitda_margin,
                    net_debt_ebitda=net_debt_ebitda,
                    revenue_growth=revenue_growth,
                    fcf_yield=fcf_yield,
                )
                logger.info(
                    "Inserted financials for %s period %s", ticker, report_date
                )
            except IntegrityError:
                await session.rollback()
                logger.warning(
                    "Duplicate financial record for company_id=%s report_date=%s, skipping",
                    company_id,
                    report_date,
                )
            except Exception as exc:
                await session.rollback()
                logger.error(
                    "Error inserting financials for %s period %s: %s",
                    ticker,
                    report_date,
                    exc,
                )
                raise

            # Update tracking variables for next iteration
            prev_revenue = revenue

            # Capture latest period metrics for the return profile
            if idx == len(periods) - 1:
                latest_profile = FinancialProfile(
                    revenue=revenue,
                    ebitda=ebitda,
                    ebitda_margin=ebitda_margin,
                    revenue_growth=revenue_growth,
                    net_debt=net_debt,
                    net_debt_ebitda=net_debt_ebitda,
                    fcf=fcf,
                    fcf_yield=fcf_yield,
                )

    return latest_profile


async def ingest_company_financials(ticker: str) -> int:
    """Ingest financials for a single ticker.

    Args:
        ticker: Yahoo Finance ticker symbol.

    Returns:
        Number of financial periods inserted.
    """
    ticker = ticker.upper().strip()

    async with async_session_factory() as session:
        result = await session.execute(
            select(Company).where(Company.ticker == ticker)
        )
        company = result.scalar_one_or_none()

        if company is None:
            logger.error("Company with ticker %s not found in database", ticker)
            return 0

        company_id = company.id

    # Count financials before and after to determine insertion count
    async with async_session_factory() as session:
        before = len(await list_financials(session, company_id=company_id))

    await load_financials(ticker, company_id)

    async with async_session_factory() as session:
        after = len(await list_financials(session, company_id=company_id))

    return after - before


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Yahoo Finance financials")
    parser.add_argument("--ticker", required=True, help="Company ticker symbol")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    count = asyncio.run(ingest_company_financials(args.ticker))
    print(f"Inserted {count} financial period(s) for {args.ticker.upper()}")


if __name__ == "__main__":
    main()
