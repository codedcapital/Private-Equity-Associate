"""Seed script for the PE Investment Platform database.

Inserts a small set of dummy companies for development and testing.
Run with: python -m db.seed
"""

import asyncio
import os

from sqlalchemy import select

from db.models import Company, CompanySource, InvestmentStrategy
from db.session import async_session_factory

seed_companies = [
    {
        "name": "Bill.com Holdings",
        "ticker": "BILL",
        "sector": "B2B SaaS",
        "source": CompanySource.SEC,
    },
    {
        "name": "Monday.com",
        "ticker": "MNDY",
        "sector": "B2B SaaS",
        "source": CompanySource.SEC,
    },
    {
        "name": "Domo Inc",
        "ticker": "DOMO",
        "sector": "B2B SaaS / Analytics",
        "source": CompanySource.SEC,
    },
    {
        "name": "Bandwidth Inc",
        "ticker": "BAND",
        "sector": "CPaaS / Telecom",
        "source": CompanySource.SEC,
    },
]


async def seed() -> None:
    async with async_session_factory() as session:
        for data in seed_companies:
            company = Company(**data)
            session.add(company)
        await session.commit()
        print(f"Seeded {len(seed_companies)} companies.")

        # Seed default investment strategy
        existing_strategy = await session.execute(
            select(InvestmentStrategy).where(InvestmentStrategy.is_default == True).limit(1)
        )
        if existing_strategy.scalar_one_or_none() is None:
            default_strategy = InvestmentStrategy(
                name="Vertical SaaS",
                is_active=True,
                is_default=True,
                criteria={
                    "sectors": ["B2B SaaS", "Vertical SaaS", "Healthcare IT", "Industrial Automation"],
                    "geographies": ["North America"],
                    "business_models": ["Recurring Revenue", "SaaS", "Subscription"],
                    "ownership_types": ["Founder-Owned", "Sponsor-Owned"],
                    "min_revenue": 50_000_000,
                    "max_revenue": 250_000_000,
                    "min_ebitda": 5_000_000,
                    "max_ebitda": 250_000_000,
                    "min_ebitda_margin": 0.20,
                    "min_revenue_growth": 0.10,
                    "max_net_debt_ebitda": 4.0,
                    "min_fcf_yield": 0.05,
                    "customer_concentration": "Low",
                    "product_type": "Mission Critical",
                },
            )
            session.add(default_strategy)
            await session.commit()
            await session.refresh(default_strategy)
            print(f"Seeded default investment strategy: {default_strategy.name}")
        else:
            print("Default investment strategy already exists.")


async def main() -> None:
    await seed()


if __name__ == "__main__":
    asyncio.run(main())
