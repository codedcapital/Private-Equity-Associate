"""Demo data seeder for the PE Investment Platform.

Populates the database with a realistic investment universe so the app looks
investor-ready: 60+ real public companies across sectors, three years of
financials each, deals distributed across every pipeline stage, LBO metrics on
the underwritten deals, and two full IC memos.

Design goals:
  • Idempotent — safe to run multiple times; skips companies/deals that exist.
  • Zero external dependencies — no OpenAI, no yfinance, no network. All figures
    are curated and deterministic, so the demo looks identical every run.

Run it inside the backend (e.g. Render Shell) where DATABASE_URL is set:

    python seed_demo.py            # seed if not already seeded
    python seed_demo.py --force    # add any missing companies/deals again
    python seed_demo.py --reset    # delete demo data first, then reseed
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date

from sqlalchemy import delete, select

from db.crud import (
    create_company,
    create_deal,
    create_financial,
    create_ic_memo,
)
from db.models import Company, CompanySource, Deal, DealStage, Financial, ICMemo
from db.session import async_session_factory

# ── Curated universe ─────────────────────────────────────────────────────────
# Each tuple: (ticker, name, sector, geography, revenue_$M, ebitda_margin,
#              revenue_growth, net_debt/ebitda leverage, pipeline stage)
# Figures are realistic approximations for a prototype — not audited financials.

S = DealStage
COMPANIES: list[tuple] = [
    # ── Closed deals (completed, with returns) ──
    ("VRNS", "Varonis Systems", "Technology / Data Security", "United States", 550, 0.18, 0.12, 0.5, S.CLOSED),
    ("PCTY", "Paylocity Holding", "Technology / HCM Software", "United States", 1400, 0.30, 0.17, 0.3, S.CLOSED),
    ("DOCN", "DigitalOcean Holdings", "Technology / Cloud Infrastructure", "United States", 700, 0.36, 0.16, 1.8, S.CLOSED),
    ("CHEF", "The Chefs' Warehouse", "Consumer / Food Distribution", "United States", 3700, 0.05, 0.10, 2.6, S.CLOSED),
    ("HELE", "Helen of Troy", "Consumer / Household Products", "United States", 2000, 0.16, 0.02, 2.2, S.CLOSED),

    # ── IC Ready (underwritten, memos attached to first two) ──
    ("FROG", "JFrog", "Technology / DevOps", "United States", 430, 0.15, 0.22, 0.2, S.IC_READY),
    ("ESTC", "Elastic NV", "Technology / Search & Observability", "Netherlands", 1400, 0.14, 0.18, 0.6, S.IC_READY),
    ("WK", "Workiva", "Technology / Compliance SaaS", "United States", 730, 0.10, 0.16, 0.4, S.IC_READY),
    ("BL", "BlackLine", "Technology / Finance Automation", "United States", 640, 0.22, 0.11, 0.9, S.IC_READY),
    ("ZI", "ZoomInfo Technologies", "Technology / Sales Intelligence", "United States", 1230, 0.38, 0.05, 3.1, S.IC_READY),
    ("ALRM", "Alarm.com Holdings", "Technology / IoT & Security", "United States", 940, 0.16, 0.08, 0.7, S.IC_READY),
    ("PRGS", "Progress Software", "Technology / Infrastructure Software", "United States", 730, 0.34, 0.10, 2.4, S.IC_READY),
    ("CWAN", "Clearwater Analytics", "Technology / FinTech SaaS", "United States", 450, 0.28, 0.23, 0.3, S.IC_READY),

    # ── Diligence (priced, in underwriting) ──
    ("APPF", "AppFolio", "Technology / Vertical SaaS", "United States", 800, 0.24, 0.27, 0.2, S.DILIGENCE),
    ("PD", "PagerDuty", "Technology / Digital Operations", "United States", 460, 0.12, 0.15, 0.5, S.DILIGENCE),
    ("BRZE", "Braze", "Technology / Customer Engagement", "United States", 580, 0.08, 0.26, 0.2, S.DILIGENCE),
    ("SMAR", "Smartsheet", "Technology / Work Management", "United States", 1100, 0.14, 0.19, 0.3, S.DILIGENCE),
    ("YETI", "YETI Holdings", "Consumer / Outdoor Brands", "United States", 1800, 0.18, 0.06, 1.4, S.DILIGENCE),
    ("CROX", "Crocs", "Consumer / Footwear", "United States", 4000, 0.27, 0.05, 1.9, S.DILIGENCE),
    ("FIGS", "FIGS", "Consumer / Healthcare Apparel", "United States", 560, 0.12, 0.04, 0.1, S.DILIGENCE),
    ("DDS", "Dillard's", "Consumer / Retail", "United States", 6600, 0.14, -0.02, 0.4, S.DILIGENCE),
    ("THS", "TreeHouse Foods", "Consumer / Private Label Food", "United States", 3400, 0.10, 0.03, 3.2, S.DILIGENCE),
    ("SXT", "Sensient Technologies", "Industrials / Specialty Chemicals", "United States", 1500, 0.17, 0.04, 2.1, S.DILIGENCE),
    ("AAON", "AAON", "Industrials / HVAC", "United States", 1200, 0.23, 0.18, 0.4, S.DILIGENCE),
    ("ROAD", "Construction Partners", "Industrials / Infrastructure", "United States", 1800, 0.11, 0.20, 2.4, S.DILIGENCE),

    # ── Sourcing (top of funnel) ──
    ("DV", "DoubleVerify", "Technology / AdTech", "United States", 650, 0.30, 0.17, 0.1, S.SOURCING),
    ("AI", "C3.ai", "Technology / Enterprise AI", "United States", 380, -0.20, 0.20, 0.1, S.SOURCING),
    ("GTLB", "GitLab", "Technology / DevSecOps", "United States", 760, 0.05, 0.33, 0.1, S.SOURCING),
    ("S", "SentinelOne", "Technology / Cybersecurity", "United States", 820, 0.04, 0.31, 0.1, S.SOURCING),
    ("PATH", "UiPath", "Technology / Automation", "United States", 1400, 0.12, 0.14, 0.1, S.SOURCING),
    ("CFLT", "Confluent", "Technology / Data Streaming", "United States", 960, 0.06, 0.24, 0.2, S.SOURCING),
    ("AMPL", "Amplitude", "Technology / Product Analytics", "United States", 300, 0.03, 0.08, 0.1, S.SOURCING),
    ("FRSH", "Freshworks", "Technology / CX Software", "United States", 720, 0.10, 0.20, 0.1, S.SOURCING),
    ("BIGC", "BigCommerce", "Technology / eCommerce", "United States", 330, 0.04, 0.09, 1.2, S.SOURCING),
    ("OLO", "Olo", "Technology / Restaurant SaaS", "United States", 270, 0.10, 0.25, 0.1, S.SOURCING),
    ("TENB", "Tenable Holdings", "Technology / Exposure Management", "United States", 880, 0.18, 0.13, 1.6, S.SOURCING),
    ("RPD", "Rapid7", "Technology / Security Analytics", "United States", 840, 0.16, 0.10, 2.8, S.SOURCING),
    ("EVBG", "Everbridge", "Technology / Critical Event Mgmt", "United States", 460, 0.18, 0.05, 2.0, S.SOURCING),
    ("CALX", "Calix", "Technology / Broadband Platforms", "United States", 900, 0.10, 0.07, 0.2, S.SOURCING),
    ("PLUS", "ePlus", "Technology / IT Solutions", "United States", 2100, 0.08, 0.11, 0.3, S.SOURCING),
    ("SLP", "Simulations Plus", "Healthcare / Life Sciences Software", "United States", 70, 0.30, 0.18, 0.1, S.SOURCING),
    ("OMCL", "Omnicell", "Healthcare / Pharmacy Automation", "United States", 1100, 0.10, -0.04, 2.2, S.SOURCING),
    ("NARI", "Inari Medical", "Healthcare / Medical Devices", "United States", 500, 0.08, 0.22, 0.1, S.SOURCING),
    ("PRVA", "Privia Health", "Healthcare / Provider Enablement", "United States", 1700, 0.04, 0.10, 0.2, S.SOURCING),
    ("HIMS", "Hims & Hers Health", "Healthcare / Telehealth", "United States", 1200, 0.06, 0.45, 0.1, S.SOURCING),
    ("DOCS", "Doximity", "Healthcare / Medical Network", "United States", 480, 0.42, 0.15, 0.1, S.SOURCING),
    ("PGNY", "Progyny", "Healthcare / Fertility Benefits", "United States", 1150, 0.10, 0.12, 0.1, S.SOURCING),
    ("EVH", "Evolent Health", "Healthcare / Value-Based Care", "United States", 2500, 0.06, 0.30, 1.5, S.SOURCING),
    ("FOXF", "Fox Factory Holding", "Industrials / Performance Components", "United States", 1450, 0.18, -0.03, 2.4, S.SOURCING),
    ("KFY", "Korn Ferry", "Business Services / Talent", "United States", 2800, 0.13, 0.02, 0.3, S.SOURCING),
    ("EXPO", "Exponent", "Business Services / Consulting", "United States", 530, 0.26, 0.05, 0.0, S.SOURCING),
    ("ICFI", "ICF International", "Business Services / Advisory", "United States", 2000, 0.11, 0.06, 2.1, S.SOURCING),
    ("CBZ", "CBIZ", "Business Services / Financial Services", "United States", 1600, 0.14, 0.08, 1.9, S.SOURCING),
    ("BV", "BrightView Holdings", "Business Services / Facilities", "United States", 2900, 0.10, 0.01, 3.0, S.SOURCING),

    # ── Passed (screened out) ──
    ("WISH", "ContextLogic", "Technology / eCommerce", "United States", 290, -0.30, -0.50, 0.0, S.PASSED),
    ("BMBL", "Bumble", "Technology / Consumer Internet", "United States", 1050, 0.25, 0.03, 2.6, S.PASSED),
    ("PTON", "Peloton Interactive", "Consumer / Connected Fitness", "United States", 2700, -0.05, -0.04, 3.5, S.PASSED),
    ("BYND", "Beyond Meat", "Consumer / Plant-Based Food", "United States", 340, -0.40, -0.12, 4.0, S.PASSED),
    ("CVNA", "Carvana", "Consumer / Auto Retail", "United States", 11000, 0.04, 0.10, 5.0, S.PASSED),
    ("CHGG", "Chegg", "Technology / EdTech", "United States", 620, 0.20, -0.08, 1.5, S.PASSED),
    ("FVRR", "Fiverr International", "Technology / Gig Marketplace", "Israel", 370, 0.16, 0.07, 0.1, S.PASSED),
    ("SDGR", "Schrodinger", "Healthcare / Computational Drug Discovery", "United States", 220, -0.55, 0.05, 0.1, S.PASSED),
    ("APRN", "Blue Apron", "Consumer / Meal Kits", "United States", 460, -0.04, -0.10, 2.8, S.PASSED),
    ("REAL", "The RealReal", "Consumer / Luxury Resale", "United States", 600, -0.06, 0.08, 2.0, S.PASSED),
    ("ME", "23andMe", "Healthcare / Consumer Genomics", "United States", 220, -0.60, -0.27, 0.0, S.PASSED),
    ("SOND", "Sonder Holdings", "Consumer / Hospitality Tech", "United States", 600, -0.10, 0.15, 4.5, S.PASSED),
]

# Entry multiples by stage maturity (EV / EBITDA) used to derive LBO economics.
ENTRY_MULTIPLE = {
    S.CLOSED: 12.5,
    S.IC_READY: 13.0,
    S.DILIGENCE: 12.0,
}


def _build_financials(revenue: float, margin: float, growth: float, leverage: float) -> list[dict]:
    """Build three fiscal years (FY-2, FY-1, latest) of financials from a profile.

    Revenue is grown forward from a base; all derived metrics are computed so the
    dashboard, deal pages, and charts render real-looking trends.
    
    Values are stored in DOLLARS (same unit as yfinance) to match the frontend
    expectation that divides by 1e6 for display in $M.
    """
    years = [date(2023, 12, 31), date(2024, 12, 31), date(2025, 12, 31)]
    rows: list[dict] = []
    prev_rev: float | None = None
    for i, rpt in enumerate(years):
        # Scale revenue so the latest year matches the curated figure.
        # Input revenue is in $M; convert to dollars for DB storage.
        rev_m = revenue * ((1 + growth) ** (i - 2))
        rev = rev_m * 1e6
        ebitda = rev * margin
        net_debt = max(leverage * ebitda, 0.0) if ebitda > 0 else leverage * abs(ebitda)
        total_debt = net_debt + max(0.15 * rev, 0.0)
        cash = total_debt - net_debt
        capex = 0.04 * rev
        operating_cf = ebitda * 0.85 if ebitda > 0 else ebitda
        fcf = operating_cf - capex
        net_income = ebitda * 0.55 if ebitda > 0 else ebitda
        total_assets = rev * 1.3
        total_equity = total_assets - total_debt
        rev_growth = None if prev_rev is None else (rev - prev_rev) / prev_rev
        rows.append({
            "report_date": rpt,
            "revenue": round(rev, 1),
            "ebitda": round(ebitda, 1),
            "net_income": round(net_income, 1),
            "total_debt": round(total_debt, 1),
            "cash": round(cash, 1),
            "total_assets": round(total_assets, 1),
            "total_equity": round(total_equity, 1),
            "operating_cf": round(operating_cf, 1),
            "capex": round(capex, 1),
            "net_debt": round(net_debt, 1),
            "fcf": round(fcf, 1),
            "ebitda_margin": round(margin, 4),
            "net_debt_ebitda": round(net_debt / ebitda, 2) if ebitda > 0 else None,
            "revenue_growth": round(rev_growth, 4) if rev_growth is not None else None,
            "fcf_yield": round(fcf / (ebitda * ENTRY_MULTIPLE.get(S.DILIGENCE, 12.0)), 4) if ebitda > 0 else None,
        })
        prev_rev = rev
    return rows


def _lbo_economics(stage: DealStage, latest: dict) -> dict:
    """Derive entry EV/EBITDA and modeled IRR/MOIC for underwritten stages."""
    mult = ENTRY_MULTIPLE.get(stage)
    if not mult or not latest.get("ebitda") or latest["ebitda"] <= 0:
        return {}
    ebitda = latest["ebitda"]
    entry_ev = round(ebitda * mult, 1)
    # Returns scale loosely with growth and margin quality.
    growth = latest.get("revenue_growth") or 0.10
    margin = latest.get("ebitda_margin") or 0.15
    irr = max(0.14, min(0.34, 0.16 + growth * 0.4 + margin * 0.3))
    moic = round(1.0 + irr * 6.5, 2)
    return {
        "entry_ev": entry_ev,
        "entry_ebitda": round(ebitda, 1),
        "lbo_irr": round(irr, 3),
        "lbo_moic": moic,
    }


def _memo_sections(name: str, sector: str, latest: dict, econ: dict) -> dict:
    """A full, realistic IC memo (no LLM needed)."""
    rev = latest["revenue"] / 1e6  # convert dollars → $M for display
    ebitda = latest["ebitda"] / 1e6
    margin = latest["ebitda_margin"]
    irr = econ.get("lbo_irr", 0.22)
    moic = econ.get("lbo_moic", 2.4)
    mult = round(econ.get("entry_ev", latest["ebitda"] * 13) / latest["ebitda"], 1) if latest["ebitda"] else 13.0
    entry_ev_m = econ.get("entry_ev", latest["ebitda"] * 13) / 1e6
    return {
        "Executive Summary": (
            f"We recommend proceeding with an investment in {name}, a leading operator in "
            f"{sector}. The business generates approximately ${rev:,.0f}M of revenue at a "
            f"{margin*100:.0f}% EBITDA margin (${ebitda:,.0f}M EBITDA). At an entry of "
            f"{mult:.1f}x EBITDA, our base case underwrites a {irr*100:.0f}% gross IRR and "
            f"{moic:.1f}x MOIC over a five-year hold."
        ),
        "Investment Thesis": (
            f"{name} combines durable, recurring revenue with a defensible market position and "
            "multiple levers for value creation: (1) continued share gains in a growing end "
            "market, (2) margin expansion through operating leverage and disciplined cost "
            "management, and (3) accretive M&A in a fragmented competitive landscape. "
            "Management incentives can be aligned with a meaningful equity rollover."
        ),
        "Business Overview": (
            f"{name} operates in {sector}, serving a diversified customer base with high "
            "retention and low concentration. The company's offering is mission-critical to its "
            "customers, supporting pricing power and predictable renewals."
        ),
        "Financial Profile": (
            f"Latest-year revenue of ${rev:,.0f}M with a {margin*100:.0f}% EBITDA margin. The "
            f"business converts EBITDA to free cash flow at an attractive rate, and net leverage "
            f"is manageable, supporting a conventional buyout capital structure of ~"
            f"{econ.get('entry_ev', latest['ebitda']*13)/latest['ebitda']*0.5:.1f}x net debt at entry."
        ),
        "Valuation": (
            f"Entry enterprise value of ${entry_ev_m:,.0f}M ({mult:.1f}x "
            f"EBITDA). We assume modest multiple compression at exit, with returns driven "
            f"primarily by EBITDA growth and de-levering. Base case: {irr*100:.0f}% IRR / "
            f"{moic:.1f}x MOIC."
        ),
        "Key Risks": (
            "Principal risks include competitive intensity and pricing pressure, customer "
            "concentration in select segments, integration risk on bolt-on acquisitions, and "
            "sensitivity to the broader macro environment. Each is mitigated by the company's "
            "recurring revenue base and conservative leverage."
        ),
        "Recommendation": (
            f"Approve a controlling investment in {name}, subject to confirmatory diligence and "
            "final structuring. The risk-adjusted return profile is consistent with the fund's "
            "mandate and target return thresholds."
        ),
    }


async def _company_exists(session, ticker: str) -> Company | None:
    res = await session.execute(select(Company).where(Company.ticker == ticker))
    return res.scalar_one_or_none()


async def _reset_demo() -> None:
    """Delete all seeded demo data (companies cascade to financials/deals/memos)."""
    tickers = [c[0] for c in COMPANIES]
    async with async_session_factory() as session:
        res = await session.execute(select(Company.id).where(Company.ticker.in_(tickers)))
        ids = [r[0] for r in res.all()]
        if ids:
            await session.execute(delete(ICMemo).where(ICMemo.company_id.in_(ids)))
            await session.execute(delete(Deal).where(Deal.company_id.in_(ids)))
            await session.execute(delete(Financial).where(Financial.company_id.in_(ids)))
            await session.execute(delete(Company).where(Company.id.in_(ids)))
            await session.commit()
        print(f"🧹 Reset: removed {len(ids)} previously seeded companies.")


async def seed(force: bool = False) -> None:
    created_co = created_deal = created_memo = skipped = 0
    memo_budget = 2  # attach full memos to the first two IC-ready deals

    async with async_session_factory() as session:
        for ticker, name, sector, geo, rev, margin, growth, lev, stage in COMPANIES:
            existing = await _company_exists(session, ticker)
            if existing and not force:
                skipped += 1
                continue

            company = existing or await create_company(
                session, name=name, source=CompanySource.MANUAL,
                ticker=ticker, sector=sector, geography=geo,
            )
            if not existing:
                created_co += 1

            # Financials (skip if the company already has them)
            has_fin = await session.execute(
                select(Financial.id).where(Financial.company_id == company.id).limit(1)
            )
            latest_row = None
            fin_rows = _build_financials(rev, margin, growth, lev)
            latest_row = fin_rows[-1]
            if has_fin.scalar_one_or_none() is None:
                for fr in fin_rows:
                    await create_financial(session, company_id=company.id, **fr)

            # Deal (skip if one exists for this company)
            existing_deal = await session.execute(
                select(Deal.id).where(Deal.company_id == company.id).limit(1)
            )
            if existing_deal.scalar_one_or_none() is not None:
                continue

            econ = _lbo_economics(stage, latest_row)
            deal = await create_deal(session, company_id=company.id, stage=stage, **econ)
            created_deal += 1

            # Attach a full IC memo to the first couple of IC-ready deals
            if stage == S.IC_READY and memo_budget > 0:
                sections = _memo_sections(name, sector, latest_row, econ)
                word_count = sum(len(v.split()) for v in sections.values())
                memo = await create_ic_memo(
                    session, company_id=company.id, sections=sections,
                    deal_id=deal.id, word_count=word_count, confidence_score=0.84,
                )
                await session.execute(
                    Deal.__table__.update().where(Deal.id == deal.id).values(memo_id=memo.id)
                )
                await session.commit()
                created_memo += 1
                memo_budget -= 1

    print(
        f"✅ Seed complete — companies: +{created_co}, deals: +{created_deal}, "
        f"memos: +{created_memo}, skipped (already present): {skipped}"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data for the PE platform.")
    parser.add_argument("--force", action="store_true", help="Re-process existing companies.")
    parser.add_argument("--reset", action="store_true", help="Delete demo data, then reseed.")
    args = parser.parse_args()

    if args.reset:
        await _reset_demo()
    await seed(force=args.force or args.reset)


if __name__ == "__main__":
    asyncio.run(main())
