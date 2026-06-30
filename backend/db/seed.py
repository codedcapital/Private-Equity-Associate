"""Seed script for the PE Investment Platform database.

Inserts a small set of dummy companies for development and testing.
Run with: python -m db.seed
"""

import asyncio
import os

from db.models import Company, CompanySource
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


async def main() -> None:
    await seed()


if __name__ == "__main__":
    asyncio.run(main())
