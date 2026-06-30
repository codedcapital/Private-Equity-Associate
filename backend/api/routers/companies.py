"""Companies router — CRUD endpoints for companies.

Endpoints:
    GET    /companies          — List all companies
    GET    /companies/{id}     — Get company with latest financials
    POST   /companies          — Create a new company
    PATCH  /companies/{id}     — Update a company
    DELETE /companies/{id}     — Delete a company
"""

from fastapi import APIRouter, HTTPException, Query

from db.crud import create_company, get_company_by_id, list_companies, update_company
from db.session import async_session_factory
from schemas.company import CompanyCreate, CompanyList, CompanyRead
from schemas.financials import FinancialProfile

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/health")
async def health() -> dict:
    """Health check for the companies router."""
    return {"status": "ok"}


@router.get("", response_model=CompanyList)
async def list_companies_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    sector: str | None = None,
) -> CompanyList:
    """List all companies in the investment universe."""
    async with async_session_factory() as session:
        companies = await list_companies(session, skip=skip, limit=limit, sector=sector)
        total = len(companies)  # Simplified; in production use a COUNT query
    return CompanyList(
        companies=[CompanyRead.model_validate(c) for c in companies],
        total=total,
    )


@router.get("/{company_id}")
async def get_company_endpoint(company_id: int) -> dict:
    """Get a company by ID, including its latest financial profile."""
    from sqlalchemy import select
    from db.models import Company, Financial

    async with async_session_factory() as session:
        company = await get_company_by_id(session, company_id)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company {company_id} not found")

        # Get latest financials
        result = await session.execute(
            select(Financial)
            .where(Financial.company_id == company_id)
            .order_by(Financial.report_date.desc())
            .limit(1)
        )
        fin = result.scalar_one_or_none()

        financial_profile = None
        if fin:
            financial_profile = FinancialProfile(
                revenue=fin.revenue,
                ebitda=fin.ebitda,
                ebitda_margin=fin.ebitda_margin,
                revenue_growth=fin.revenue_growth,
                net_debt=fin.net_debt,
                net_debt_ebitda=fin.net_debt_ebitda,
                fcf=fin.fcf,
                fcf_yield=fin.fcf_yield,
            )

    return {
        "company": CompanyRead.model_validate(company).model_dump(mode="json"),
        "financial_profile": financial_profile.model_dump(mode="json") if financial_profile else None,
    }


@router.post("", response_model=CompanyRead)
async def create_company_endpoint(request: CompanyCreate) -> CompanyRead:
    """Create a new company in the database."""
    async with async_session_factory() as session:
        company = await create_company(
            session,
            name=request.name,
            source=request.source,
            ticker=request.ticker,
            sector=request.sector,
            geography=request.geography,
        )
    return CompanyRead.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyRead)
async def update_company_endpoint(company_id: int, request: CompanyCreate) -> CompanyRead:
    """Update a company's details."""
    async with async_session_factory() as session:
        company = await update_company(
            session,
            company_id,
            name=request.name,
            ticker=request.ticker,
            sector=request.sector,
            geography=request.geography,
        )
        if not company:
            raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
    return CompanyRead.model_validate(company)
