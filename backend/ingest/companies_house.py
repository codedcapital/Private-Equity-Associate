"""Companies House UK data ingestion module for the PE Investment Platform.

Provides async functions to search, fetch profiles, retrieve filing history,
and ingest UK companies into the local database via the Companies House REST API.

Environment:
    COMPANIES_HOUSE_API_KEY: Your Companies House API key (optional for test mode).

Usage:
    python -m ingest.companies_house --name "TestCo" --test-mode
"""

from __future__ import annotations

import argparse
import base64
import sys
from typing import Any

import httpx

from core.config import settings
from db.crud import create_company
from db.models import CompanySource
from db.session import async_session_factory


# ── Configuration ────────────────────────────────────────────────────────────

API_BASE = "https://api.company-information.service.gov.uk"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# ── Mock data for test mode ────────────────────────────────────────────────


_MOCK_SEARCH_RESULTS: list[dict[str, Any]] = [
    {
        "company_number": "12345678",
        "title": "TestCo Limited",
        "company_type": "ltd",
        "date_of_creation": "2015-06-15",
        "address_snippet": "1 Test Street, London, SW1A 1AA",
    },
    {
        "company_number": "87654321",
        "title": "Another TestCo Ltd",
        "company_type": "ltd",
        "date_of_creation": "2018-03-22",
        "address_snippet": "2 Sample Road, Manchester, M1 1AA",
    },
]

_MOCK_PROFILE: dict[str, Any] = {
    "company_name": "TestCo Limited",
    "company_number": "12345678",
    "date_of_creation": "2015-06-15",
    "sic_codes": ["62012", "62020"],
    "registered_office_address": {
        "address_line_1": "1 Test Street",
        "locality": "London",
        "postal_code": "SW1A 1AA",
        "country": "United Kingdom",
    },
}

_MOCK_FILINGS: list[dict[str, Any]] = [
    {
        "category": "accounts",
        "date": "2024-01-31",
        "description": "accounts-with-accounts-type-dormant",
        "links": {
            "self": "/company/12345678/filing-history/MTIzNDU2Nzh8YWNjb3VudHN8MTcwNjcxMDQwMDAwMA",
            "document_metadata": "https://document-api.company-information.service.gov.uk/document/abc123",
        },
    },
    {
        "category": "confirmation-statement",
        "date": "2023-06-15",
        "description": "confirmation-statement-with-updates",
        "links": {
            "self": "/company/12345678/filing-history/MTIzNDU2Nzh8Y29uZmlybWF0aW9uLXN0YXRlbWVudHwxNjg3MzEyODAwMDAw",
            "document_metadata": "https://document-api.company-information.service.gov.uk/document/def456",
        },
    },
]


# ── HTTP helpers ───────────────────────────────────────────────────────────


def _auth_header(api_key: str | None) -> dict[str, str] | None:
    """Build Basic Auth header for Companies House (username = key, password = empty)."""
    if not api_key:
        return None
    credentials = base64.b64encode(f"{api_key}:".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


async def _raise_for_status(response: httpx.Response) -> None:
    """Custom status handling with helpful messages for common errors."""
    if response.status_code == 401:
        raise CompaniesHouseAuthError(
            "Companies House API key required. Register at "
            "https://developer.company-information.service.gov.uk"
        )
    if response.status_code == 429:
        raise CompaniesHouseRateLimitError("Companies House rate limit exceeded. Please retry later.")
    response.raise_for_status()


class CompaniesHouseAuthError(Exception):
    """Raised when the API returns 401 (missing or invalid key)."""


class CompaniesHouseRateLimitError(Exception):
    """Raised when the API returns 429 (rate limited)."""


# ── Public API ─────────────────────────────────────────────────────────────


async def search_company(name: str, *, test_mode: bool = False) -> list[dict[str, Any]]:
    """Search Companies House by company name.

    Args:
        name: Company name to search for.
        test_mode: If True, return mock data instead of hitting the API.

    Returns:
        List of matching companies with keys:
        company_number, title, company_type, date_of_creation, address_snippet.
    """
    if test_mode:
        return _MOCK_SEARCH_RESULTS

    api_key = settings.companies_house_api_key
    headers = _auth_header(api_key)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{API_BASE}/search/companies",
            params={"q": name},
            headers=headers,
        )
        await _raise_for_status(response)
        data = response.json()

    items = data.get("items", [])
    return [
        {
            "company_number": item.get("company_number"),
            "title": item.get("title"),
            "company_type": item.get("company_type"),
            "date_of_creation": item.get("date_of_creation"),
            "address_snippet": item.get("address_snippet"),
        }
        for item in items
    ]


async def get_company_profile(
    company_number: str, *, test_mode: bool = False
) -> dict[str, Any]:
    """Fetch a company profile from Companies House.

    Args:
        company_number: The 8-digit Companies House number.
        test_mode: If True, return mock data instead of hitting the API.

    Returns:
        Dict with keys: company_name, company_number, date_of_creation,
        sic_codes, registered_office_address.
    """
    if test_mode:
        return _MOCK_PROFILE

    api_key = settings.companies_house_api_key
    headers = _auth_header(api_key)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{API_BASE}/company/{company_number}",
            headers=headers,
        )
        await _raise_for_status(response)
        data = response.json()

    return {
        "company_name": data.get("company_name"),
        "company_number": data.get("company_number"),
        "date_of_creation": data.get("date_of_creation"),
        "sic_codes": data.get("sic_codes", []),
        "registered_office_address": data.get("registered_office_address", {}),
    }


async def get_filing_history(
    company_number: str, *, test_mode: bool = False
) -> list[dict[str, Any]]:
    """Fetch filing history for a company.

    Args:
        company_number: The 8-digit Companies House number.
        test_mode: If True, return mock data instead of hitting the API.

    Returns:
        List of filings with keys: category, date, description, links.
    """
    if test_mode:
        return _MOCK_FILINGS

    api_key = settings.companies_house_api_key
    headers = _auth_header(api_key)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{API_BASE}/company/{company_number}/filing-history",
            headers=headers,
        )
        await _raise_for_status(response)
        data = response.json()

    items = data.get("items", [])
    return [
        {
            "category": item.get("category"),
            "date": item.get("date"),
            "description": item.get("description"),
            "links": item.get("links", {}),
        }
        for item in items
    ]


async def ingest_company(name: str, *, test_mode: bool = False) -> int:
    """Ingest a UK company into the local database.

    Workflow:
        1. Search Companies House by name.
        2. Take the first result.
        3. Fetch the company profile.
        4. Map to the local ``companies`` table schema.
        5. Insert via ``db.crud.create_company``.

    Args:
        name: Company name to search for.
        test_mode: If True, use mock data (no external API call).

    Returns:
        The primary key ``company_id`` of the newly created record.
    """
    search_results = await search_company(name, test_mode=test_mode)
    if not search_results:
        raise ValueError(f"No Companies House results found for '{name}'")

    first_result = search_results[0]
    company_number = first_result["company_number"]

    profile = await get_company_profile(company_number, test_mode=test_mode)

    # Map to local schema
    company_name = profile.get("company_name") or first_result.get("title") or name
    sic_codes = profile.get("sic_codes") or []
    sector = sic_codes[0] if sic_codes else "Unknown"
    geography = "UK"
    source = CompanySource.COMPANIES_HOUSE

    async with async_session_factory() as session:
        company = await create_company(
            session=session,
            name=company_name,
            source=source,
            sector=sector,
            geography=geography,
        )
        return company.id


# ── CLI entry point ────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.companies_house",
        description="Ingest a UK company from Companies House into the PE Platform.",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Company name to search for.",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        default=False,
        help="Use mock data instead of calling the live API.",
    )
    return parser


async def _main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        company_id = await ingest_company(args.name, test_mode=args.test_mode)
        print(f"Successfully ingested company: id={company_id}")
    except CompaniesHouseAuthError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except CompaniesHouseRateLimitError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(_main())
