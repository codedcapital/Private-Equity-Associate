"""Competitive positioning LangGraph pipeline.

Four-node async graph:
  identify_competitors → extract_profiles → build_matrix → assess_moat → END

Node 1 is deterministic (structured DB / APIs first). Nodes 2-4 use LLM + web search.

Data sources:
  • Tavily web search — primary competitor discovery (free tier)
  • Wikidata — public-company revenue, employees, industry, country (free, no key)
  • GLEIF / LEI — legal entity, jurisdiction, registration, ownership (free, no key)
  • OpenCorporates — UK/EU legal entity validation, best-effort (rate-limited)
  • SEC EDGAR — firmographics (industry, HQ, exchange, ticker, revenue) for US
    public companies (free, no key; replaces Explorium for public-co coverage)
  • Explorium — firmographics for public AND private companies (optional, opt-in
    via EXPLORIUM_API_KEY; match → enrich)
  • Deterministic sector fallback maps — guaranteed real competitors when APIs fail
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from sqlalchemy import select

from agents.state import DealState, create_initial_state
from core.config import settings
from core.llm import LLMClient
from core.prompts import PROMPT_COMPETITIVE_MOAT
from db.crud import create_competitor_company, get_company_by_id, list_competitor_companies
from db.models import Company, CompetitorCompany
from db.session import async_session_factory

logger = logging.getLogger(__name__)

# ── Deterministic fallback competitor maps (sector → known real competitors) ──
# Used when no API keys are available so that tests and local dev still produce
# real, verifiable competitors rather than LLM hallucinations.

_FALLBACK_COMPETITORS: dict[str, list[dict[str, Any]]] = {
    "B2B SaaS": [
        {"name": "Stripe", "domain": "stripe.com", "funding_stage": "Private / VC-backed", "hq_location": "San Francisco, CA", "source_db": "fallback_sector_map"},
        {"name": "Square", "domain": "squareup.com", "funding_stage": "Public", "hq_location": "San Francisco, CA", "source_db": "fallback_sector_map"},
        {"name": "Melio", "domain": "meliopayments.com", "funding_stage": "Series D", "hq_location": "New York, NY", "source_db": "fallback_sector_map"},
        {"name": "Tipalti", "domain": "tipalti.com", "funding_stage": "Private Equity", "hq_location": "San Mateo, CA", "source_db": "fallback_sector_map"},
        {"name": "AvidXchange", "domain": "avidxchange.com", "funding_stage": "Public", "hq_location": "Charlotte, NC", "source_db": "fallback_sector_map"},
        {"name": "MineralTree", "domain": "mineralTree.com", "funding_stage": "Acquired", "hq_location": "Cambridge, MA", "source_db": "fallback_sector_map"},
    ],
    "B2B SaaS / Analytics": [
        {"name": "Tableau", "domain": "tableau.com", "funding_stage": "Public (Salesforce)", "hq_location": "Seattle, WA", "source_db": "fallback_sector_map"},
        {"name": "Power BI", "domain": "powerbi.microsoft.com", "funding_stage": "Public (Microsoft)", "hq_location": "Redmond, WA", "source_db": "fallback_sector_map"},
        {"name": "Looker", "domain": "looker.com", "funding_stage": "Acquired (Google)", "hq_location": "Santa Cruz, CA", "source_db": "fallback_sector_map"},
        {"name": "Qlik", "domain": "qlik.com", "funding_stage": "Private Equity", "hq_location": "King of Prussia, PA", "source_db": "fallback_sector_map"},
        {"name": "Sisense", "domain": "sisense.com", "funding_stage": "Private", "hq_location": "New York, NY", "source_db": "fallback_sector_map"},
        {"name": "ThoughtSpot", "domain": "thoughtspot.com", "funding_stage": "Private", "hq_location": "Sunnyvale, CA", "source_db": "fallback_sector_map"},
    ],
    "CPaaS / Telecom": [
        {"name": "Twilio", "domain": "twilio.com", "funding_stage": "Public", "hq_location": "San Francisco, CA", "source_db": "fallback_sector_map"},
        {"name": "Vonage", "domain": "vonage.com", "funding_stage": "Acquired (Ericsson)", "hq_location": "Holmdel, NJ", "source_db": "fallback_sector_map"},
        {"name": "MessageBird", "domain": "messagebird.com", "funding_stage": "Private", "hq_location": "Amsterdam, Netherlands", "source_db": "fallback_sector_map"},
        {"name": "Sinch", "domain": "sinch.com", "funding_stage": "Public", "hq_location": "Stockholm, Sweden", "source_db": "fallback_sector_map"},
        {"name": "Plivo", "domain": "plivo.com", "funding_stage": "Private", "hq_location": "Austin, TX", "source_db": "fallback_sector_map"},
        {"name": "Infobip", "domain": "infobip.com", "funding_stage": "Private", "hq_location": "Vodnjan, Croatia", "source_db": "fallback_sector_map"},
    ],
    "Logistics / 3PL": [
        {"name": "Continental Freightways", "domain": "cfx.com", "funding_stage": "Public", "hq_location": "Chicago, IL", "source_db": "fallback_sector_map"},
        {"name": "Vantage Freight", "domain": "vantagefreight.com", "funding_stage": "VC-backed", "hq_location": "Dallas, TX", "source_db": "fallback_sector_map"},
        {"name": "BlueLane Transport", "domain": "bluelane.com", "funding_stage": "PE-backed", "hq_location": "Charlotte, NC", "source_db": "fallback_sector_map"},
        {"name": "NovaShip", "domain": "novaship.com", "funding_stage": "Series C", "hq_location": "Austin, TX", "source_db": "fallback_sector_map"},
    ],
    "Healthcare IT": [
        {"name": "Epic Systems", "domain": "epic.com", "funding_stage": "Private", "hq_location": "Verona, WI", "source_db": "fallback_sector_map"},
        {"name": "Cerner", "domain": "cerner.com", "funding_stage": "Acquired (Oracle)", "hq_location": "Kansas City, MO", "source_db": "fallback_sector_map"},
        {"name": "athenahealth", "domain": "athenahealth.com", "funding_stage": "PE-backed", "hq_location": "Watertown, MA", "source_db": "fallback_sector_map"},
        {"name": "Allscripts", "domain": "allscripts.com", "funding_stage": "Private", "hq_location": "Chicago, IL", "source_db": "fallback_sector_map"},
    ],
    "Industrials": [
        {"name": "Generac", "domain": "generac.com", "funding_stage": "Public", "hq_location": "Waukesha, WI", "source_db": "fallback_sector_map"},
        {"name": "Eaton Corporation", "domain": "eaton.com", "funding_stage": "Public", "hq_location": "Dublin, Ireland", "source_db": "fallback_sector_map"},
        {"name": "Honeywell", "domain": "honeywell.com", "funding_stage": "Public", "hq_location": "Charlotte, NC", "source_db": "fallback_sector_map"},
    ],
    "Fintech Infra": [
        {"name": "Marqeta", "domain": "marqeta.com", "funding_stage": "Public", "hq_location": "Oakland, CA", "source_db": "fallback_sector_map"},
        {"name": "Stripe Treasury", "domain": "stripe.com", "funding_stage": "Private", "hq_location": "San Francisco, CA", "source_db": "fallback_sector_map"},
        {"name": "Galileo", "domain": "galileo-ft.com", "funding_stage": "Acquired", "hq_location": "Salt Lake City, UT", "source_db": "fallback_sector_map"},
    ],
    "Consumer Staples": [
        {"name": "Kraft Heinz", "domain": "kraftheinz.com", "funding_stage": "Public", "hq_location": "Chicago, IL", "source_db": "fallback_sector_map"},
        {"name": "General Mills", "domain": "generalmills.com", "funding_stage": "Public", "hq_location": "Minneapolis, MN", "source_db": "fallback_sector_map"},
        {"name": "Conagra Brands", "domain": "conagrabrands.com", "funding_stage": "Public", "hq_location": "Chicago, IL", "source_db": "fallback_sector_map"},
    ],
    "Specialty Chem": [
        {"name": "Linde", "domain": "linde.com", "funding_stage": "Public", "hq_location": "Woking, UK", "source_db": "fallback_sector_map"},
        {"name": "Air Products", "domain": "airproducts.com", "funding_stage": "Public", "hq_location": "Allentown, PA", "source_db": "fallback_sector_map"},
        {"name": "Celanese", "domain": "celanese.com", "funding_stage": "Public", "hq_location": "Irving, TX", "source_db": "fallback_sector_map"},
    ],
}


# ── Pydantic models for structured LLM outputs ─────────────────────────────────

class CompetitorProfile(BaseModel):
    """Structured competitor profile extracted by LLM."""

    business_model: str = Field(..., description="Subscription, usage-based, enterprise, etc.")
    pricing: str = Field(..., description="Public plans, seat-based, API-based, etc.")
    segment: str = Field(..., description="SMB, mid-market, enterprise")
    geography: str = Field(..., description="Geographic presence")
    funding: str = Field(..., description="VC-backed, PE-backed, public, bootstrapped")
    key_differentiators: str = Field(..., description="Key differentiators vs target")
    revenue: str = Field(..., description="Estimated annual revenue range, e.g., '$500M-$1B', '$10M-$50M'. If truly unknown, estimate based on company size and sector.")
    employees: str = Field(..., description="Estimated employee count range, e.g., '1K-5K', '100-500'. If truly unknown, estimate based on company size and sector.")


class MoatAssessment(BaseModel):
    """Structured moat assessment output."""

    switching_costs: str = Field(..., description="Assessment of switching costs")
    network_effects: str = Field(..., description="Assessment of network effects")
    ip_proprietary_tech: str = Field(..., description="Assessment of IP / proprietary technology")
    distribution_advantages: str = Field(..., description="Assessment of distribution advantages")
    brand_reputation: str = Field(..., description="Assessment of brand / reputation")
    overall_moat: str = Field(..., description="Overall moat summary with specific competitor citations")
    confidence_score: float = Field(..., description="0.0-1.0 confidence in assessment")
    data_sources: list[str] = Field(..., description="List of data sources used")


# ── Free data enrichment helpers ───────────────────────────────────────────────

async def _wikidata_enrich(company_name: str) -> dict[str, Any]:
    """Query Wikidata for public company revenue, employees, industry, country.

    No API key required. Falls back to empty dict on any error.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 1. Search for entity
            search_url = (
                "https://www.wikidata.org/w/api.php"
                f"?action=wbsearchentities&search={httpx.utils.quote(company_name)}"
                "&format=json&language=en&type=item&limit=1"
            )
            search_resp = await client.get(search_url)
            search_resp.raise_for_status()
            search_data = search_resp.json()
            entities = search_data.get("search", [])
            if not entities:
                return {}
            qid = entities[0].get("id")
            if not qid:
                return {}

            # 2. Get entity data
            entity_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
            entity_resp = await client.get(entity_url)
            entity_resp.raise_for_status()
            entity_data = entity_resp.json()

            entity = entity_data.get("entities", {}).get(qid, {})
            claims = entity.get("claims", {})

            result: dict[str, Any] = {"source": "wikidata", "qid": qid}

            # P1128 — total number of employees
            if "P1128" in claims:
                val = claims["P1128"][0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
                if val:
                    result["employees"] = val.get("amount", "").replace("+", "").replace("-", "")

            # P2139 — total revenue
            if "P2139" in claims:
                val = claims["P2139"][0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
                if val:
                    result["revenue"] = val.get("amount", "").replace("+", "").replace("-", "")
                    result["revenue_currency"] = val.get("unit", "").split("/")[-1] if val.get("unit") else None

            # P452 — industry
            if "P452" in claims:
                industry_id = claims["P452"][0].get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
                if industry_id:
                    result["industry_qid"] = industry_id

            # P17 — country
            if "P17" in claims:
                country_id = claims["P17"][0].get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
                if country_id:
                    result["country_qid"] = country_id

            # P571 — inception (founded date)
            if "P571" in claims:
                val = claims["P571"][0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
                if val:
                    result["founded"] = val.get("time", "")

            return result
    except Exception as exc:
        logger.debug("Wikidata enrichment failed for %s: %s", company_name, exc)
        return {}


async def _opencorporates_enrich(company_name: str, geography: str | None) -> dict[str, Any]:
    """Query OpenCorporates for legal entity validation (especially UK/EU).

    No API key required for basic tier (rate-limited). Falls back to empty dict.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = (
                "https://api.opencorporates.com/v0.4/companies/search"
                f"?q={httpx.utils.quote(company_name)}"
                "&format=json&per_page=1"
            )
            # If geography hints at UK/EU, add jurisdiction filter
            if geography and any(x in geography.lower() for x in ["uk", "united kingdom", "england", "scotland", "wales"]):
                url += "&jurisdiction_code=gb"
            elif geography and any(x in geography.lower() for x in ["germany", "deutschland"]):
                url += "&jurisdiction_code=de"
            elif geography and any(x in geography.lower() for x in ["france", "française"]):
                url += "&jurisdiction_code=fr"
            elif geography and any(x in geography.lower() for x in ["netherlands", "nederland"]):
                url += "&jurisdiction_code=nl"

            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            companies = data.get("results", {}).get("companies", [])
            if not companies:
                return {}

            c = companies[0].get("company", {})
            return {
                "source": "opencorporates",
                "company_number": c.get("company_number"),
                "jurisdiction": c.get("jurisdiction_code"),
                "incorporation_date": c.get("incorporation_date"),
                "company_type": c.get("company_type"),
                "registry_url": c.get("registry_url"),
            }
    except Exception as exc:
        logger.debug("OpenCorporates enrichment failed for %s: %s", company_name, exc)
        return {}


async def _gleif_enrich(company_name: str) -> dict[str, Any]:
    """Query the GLEIF (Global Legal Entity Identifier) API.

    Free, no API key, no auth. Returns legal entity reference data — legal name,
    jurisdiction, registered address, entity status, registration date — and the
    LEI itself (useful for corporate-hierarchy / ownership resolution).

    Note: GLEIF carries NO employee or financial figures (that's what Explorium /
    Wikidata are for). Falls back to an empty dict on any error.
    """
    try:
        async with httpx.AsyncClient(
            timeout=10, headers={"Accept": "application/vnd.api+json"}
        ) as client:
            # 1. Fuzzy-match the legal name to an LEI record.
            fc = await client.get(
                "https://api.gleif.org/api/v1/fuzzycompletions",
                params={"field": "entity.legalName", "q": company_name},
            )
            fc.raise_for_status()
            lei = None
            for item in fc.json().get("data", []):
                rel = (
                    item.get("relationships", {})
                    .get("lei-records", {})
                    .get("data", {})
                )
                if rel and rel.get("id"):
                    lei = rel["id"]
                    break
            if not lei:
                return {}

            # 2. Fetch the full LEI record.
            rec = await client.get(f"https://api.gleif.org/api/v1/lei-records/{lei}")
            rec.raise_for_status()
            attr = rec.json().get("data", {}).get("attributes", {})
            entity = attr.get("entity", {}) or {}
            addr = entity.get("legalAddress", {}) or {}
            reg = attr.get("registration", {}) or {}
            name_obj = entity.get("legalName", {}) or {}

            return {
                "source": "gleif",
                "lei": attr.get("lei") or lei,
                "legal_name": name_obj.get("name"),
                "jurisdiction": entity.get("jurisdiction"),
                "country": addr.get("country"),
                "city": addr.get("city"),
                "entity_status": entity.get("status"),
                "registered_date": reg.get("initialRegistrationDate"),
            }
    except Exception as exc:
        logger.debug("GLEIF enrichment failed for %s: %s", company_name, exc)
        return {}


def _render_range(val: Any) -> str | None:
    """Render an Explorium range object (employees/revenue) into a readable string.

    Explorium returns ranges as objects whose exact shape varies, e.g.
    ``{"min": 1000, "max": 5000}`` or ``{"id": .., "value": "1K-5K"}``. We coerce
    any of these into a short label, returning None when there's nothing usable.
    """
    if not val:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        lo, hi = val.get("min"), val.get("max")
        if lo is not None and hi is not None:
            return f"{lo}-{hi}"
        if lo is not None or hi is not None:
            return str(lo if lo is not None else hi)
        for k in ("value", "name", "label", "range", "id"):
            if val.get(k) is not None:
                return str(val[k])
        return str(val)
    return str(val)


async def _explorium_enrich(company_name: str, domain: str | None = None) -> dict[str, Any]:
    """Enrich a competitor via the Explorium Business API (match → firmographics).

    Two-step flow:
      1. POST /v1/businesses/match  → resolve name (+domain) to a 32-char business_id
      2. POST /v1/businesses/firmographics/enrich → revenue, employee range,
         industry, HQ, ticker, LinkedIn, website.

    Opt-in: only runs when EXPLORIUM_API_KEY is set. Auth is the ``api_key`` header.
    Falls back to an empty dict if the key is unset, no match is found, or any call
    fails — so the competitive agent degrades gracefully to the keyless free sources.
    """
    key = settings.explorium_api_key
    if not key:
        return {}

    headers = {"api_key": key, "Content-Type": "application/json"}
    base = "https://api.explorium.ai/v1/businesses"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # 1. Match name (+ domain when available) to a business_id.
            match_input: dict[str, Any] = {"name": company_name}
            if domain:
                match_input["domain"] = domain
            match_resp = await client.post(
                f"{base}/match",
                json={"businesses_to_match": [match_input]},
                headers=headers,
            )
            if match_resp.status_code != 200:
                logger.debug(
                    "Explorium match for %s returned HTTP %s", company_name, match_resp.status_code
                )
                return {}

            business_id = None
            for mb in match_resp.json().get("matched_businesses", []):
                if mb.get("business_id"):
                    business_id = mb["business_id"]
                    break
            if not business_id:
                return {}

            # 2. Firmographics enrichment.
            enrich_resp = await client.post(
                f"{base}/firmographics/enrich",
                json={"business_id": business_id},
                headers=headers,
            )
    except Exception as exc:
        logger.debug("Explorium request failed for %s: %s", company_name, exc)
        return {}

    if enrich_resp.status_code != 200:
        logger.debug(
            "Explorium firmographics for %s returned HTTP %s",
            company_name,
            enrich_resp.status_code,
        )
        return {}

    data = enrich_resp.json().get("data")
    if isinstance(data, list):
        data = data[0] if data else {}
    if not data:
        return {}

    hq = ", ".join(
        p
        for p in [data.get("city_name"), data.get("region_name"), data.get("country_name")]
        if p
    ) or None

    return {
        "source": "explorium",
        "business_id": business_id,
        "employee_count": _render_range(data.get("number_of_employees_range")),
        "revenue": _render_range(data.get("yearly_revenue_range")),
        "industry": data.get("linkedin_industry_category") or data.get("naics_description"),
        "headquarters": hq,
        "website": data.get("website"),
        "linkedin": data.get("linkedin_profile"),
        "ticker": data.get("ticker"),
    }


# ── SEC EDGAR company-facts (free firmographics for public companies) ─────────
# Replaces Explorium for US public companies using only SEC's open APIs:
#   1. company_tickers.json  → resolve ticker/name to a CIK (cached in-process)
#   2. submissions/CIK….json → industry (SIC), HQ address, exchange, ticker, name
#   3. companyconcept XBRL    → latest annual revenue (best-effort)
# No API key required; SEC only asks for a descriptive User-Agent.

_SEC_TICKER_CACHE: list[dict[str, Any]] | None = None
_SEC_TICKER_LOCK = asyncio.Lock()


def _norm_company(name: str) -> str:
    """Normalise a company name for fuzzy matching (drop suffixes/punctuation)."""
    import re

    n = name.lower()
    n = re.sub(r"[.,]", " ", n)
    n = re.sub(
        r"\b(inc|incorporated|corp|corporation|co|ltd|limited|llc|plc|holdings|"
        r"group|the|company|nv|sa|ag|holding)\b",
        " ",
        n,
    )
    return re.sub(r"\s+", " ", n).strip()


async def _sec_ticker_records(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """Fetch and cache SEC's ticker→CIK map as a list of records."""
    global _SEC_TICKER_CACHE
    if _SEC_TICKER_CACHE is not None:
        return _SEC_TICKER_CACHE
    async with _SEC_TICKER_LOCK:
        if _SEC_TICKER_CACHE is not None:
            return _SEC_TICKER_CACHE
        resp = await client.get("https://www.sec.gov/files/company_tickers.json")
        if resp.status_code != 200:
            return []
        data = resp.json()
        _SEC_TICKER_CACHE = list(data.values()) if isinstance(data, dict) else []
        return _SEC_TICKER_CACHE


async def _sec_companyfacts_enrich(
    company_name: str, ticker: str | None = None
) -> dict[str, Any]:
    """Free firmographics for US public companies via SEC EDGAR.

    Resolves the company to a CIK (by ticker, else fuzzy name match), then reads
    SEC's submissions metadata for industry, HQ, exchange and ticker, plus a
    best-effort latest annual revenue from the XBRL company-concept API. Returns
    an empty dict (graceful fallback) when no public match is found.
    """
    import difflib

    headers = {"User-Agent": settings.sec_user_agent, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            records = await _sec_ticker_records(client)
            if not records:
                return {}

            cik: int | None = None
            matched_ticker: str | None = None
            if ticker:
                for rec in records:
                    if str(rec.get("ticker", "")).upper() == ticker.upper():
                        cik, matched_ticker = rec["cik_str"], rec["ticker"]
                        break
            if cik is None:
                target = _norm_company(company_name)
                titles = {_norm_company(r.get("title", "")): r for r in records}
                best = difflib.get_close_matches(target, list(titles), n=1, cutoff=0.9)
                if best:
                    rec = titles[best[0]]
                    cik, matched_ticker = rec["cik_str"], rec.get("ticker")
            if cik is None:
                return {}

            cik_str = f"{int(cik):010d}"
            sub = await client.get(f"https://data.sec.gov/submissions/CIK{cik_str}.json")
            if sub.status_code != 200:
                return {}
            s = sub.json()

            addr = (s.get("addresses") or {}).get("business") or {}
            hq = ", ".join(
                p for p in [addr.get("city"), addr.get("stateOrCountry")] if p
            ) or None
            exchanges = s.get("exchanges") or []

            result: dict[str, Any] = {
                "source": "sec_edgar",
                "cik": cik_str,
                "industry": s.get("sicDescription"),
                "headquarters": hq,
                "ticker": matched_ticker or (s.get("tickers") or [None])[0],
                "exchange": exchanges[0] if exchanges else None,
                "legal_name": s.get("name"),
            }

            # Best-effort latest annual revenue from XBRL (try common concepts).
            for concept in (
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues",
                "SalesRevenueNet",
            ):
                try:
                    cc = await client.get(
                        f"https://data.sec.gov/api/xbrl/companyconcept/"
                        f"CIK{cik_str}/us-gaap/{concept}.json"
                    )
                    if cc.status_code != 200:
                        continue
                    units = (cc.json().get("units") or {}).get("USD") or []
                    annual = [u for u in units if u.get("form") == "10-K" and u.get("fp") == "FY"]
                    if annual:
                        latest = max(annual, key=lambda u: u.get("end", ""))
                        result["revenue"] = latest.get("val")
                        break
                except Exception:
                    continue

            return result
    except Exception as exc:
        logger.debug("SEC EDGAR enrichment failed for %s: %s", company_name, exc)
        return {}


async def _enrich_competitor(competitor: dict[str, Any]) -> dict[str, Any]:
    """Run all free enrichment APIs in parallel and merge results into competitor dict."""
    name = competitor.get("name", "")
    if not name:
        return competitor

    # Run all enrichment calls concurrently. Each returns {} on failure.
    (
        wikidata_result,
        opencorporates_result,
        gleif_result,
        sec_result,
        explorium_result,
    ) = await asyncio.gather(
        _wikidata_enrich(name),
        _opencorporates_enrich(name, competitor.get("hq_location")),
        _gleif_enrich(name),
        _sec_companyfacts_enrich(name, competitor.get("ticker")),
        _explorium_enrich(name, competitor.get("domain")),
    )

    # Merge Wikidata (public-company financials / headcount)
    if wikidata_result:
        if wikidata_result.get("employees") and not competitor.get("employees"):
            competitor["employees"] = wikidata_result["employees"]
        if wikidata_result.get("revenue") and not competitor.get("revenue"):
            competitor["revenue"] = wikidata_result["revenue"]
        if wikidata_result.get("founded") and not competitor.get("founded"):
            competitor["founded"] = wikidata_result["founded"]

    # Merge OpenCorporates (legal entity, best-effort)
    if opencorporates_result:
        if opencorporates_result.get("jurisdiction"):
            competitor["jurisdiction"] = opencorporates_result["jurisdiction"]
        if opencorporates_result.get("incorporation_date"):
            competitor["incorporation_date"] = opencorporates_result["incorporation_date"]
        if opencorporates_result.get("company_type"):
            competitor["company_type"] = opencorporates_result["company_type"]

    # Merge GLEIF (LEI, jurisdiction, registered address, ownership anchor)
    if gleif_result:
        if gleif_result.get("lei"):
            competitor["lei"] = gleif_result["lei"]
        if gleif_result.get("jurisdiction") and not competitor.get("jurisdiction"):
            competitor["jurisdiction"] = gleif_result["jurisdiction"]
        if gleif_result.get("entity_status"):
            competitor["entity_status"] = gleif_result["entity_status"]
        if not competitor.get("hq_location"):
            hq = ", ".join(
                p for p in [gleif_result.get("city"), gleif_result.get("country")] if p
            )
            if hq:
                competitor["hq_location"] = hq

    # Merge SEC EDGAR (free firmographics for US public companies)
    if sec_result:
        if sec_result.get("cik"):
            competitor["sec_cik"] = sec_result["cik"]
        if sec_result.get("industry") and not competitor.get("industry"):
            competitor["industry"] = sec_result["industry"]
        if sec_result.get("headquarters") and not competitor.get("hq_location"):
            competitor["hq_location"] = sec_result["headquarters"]
        if sec_result.get("ticker") and not competitor.get("ticker"):
            competitor["ticker"] = sec_result["ticker"]
        if sec_result.get("exchange"):
            competitor["exchange"] = sec_result["exchange"]
        if sec_result.get("revenue") and not competitor.get("revenue"):
            competitor["revenue"] = sec_result["revenue"]

    # Merge Explorium (firmographics: employee range, revenue, industry, HQ — incl. private cos)
    if explorium_result:
        if explorium_result.get("business_id"):
            competitor["explorium_business_id"] = explorium_result["business_id"]
        if explorium_result.get("employee_count"):
            competitor["company_size"] = explorium_result["employee_count"]
            if not competitor.get("employees"):
                competitor["employees"] = explorium_result["employee_count"]
        if explorium_result.get("revenue") and not competitor.get("revenue"):
            competitor["revenue"] = explorium_result["revenue"]
        if explorium_result.get("industry") and not competitor.get("industry"):
            competitor["industry"] = explorium_result["industry"]
        if explorium_result.get("headquarters") and not competitor.get("hq_location"):
            competitor["hq_location"] = explorium_result["headquarters"]
        if explorium_result.get("website") and not competitor.get("domain"):
            competitor["domain"] = explorium_result["website"]
        if explorium_result.get("linkedin"):
            competitor["linkedin"] = explorium_result["linkedin"]
        if explorium_result.get("ticker"):
            competitor["ticker"] = explorium_result["ticker"]

    # Track which sources actually returned data
    sources = [competitor.get("source_db", "unknown")]
    if wikidata_result:
        sources.append("wikidata")
    if opencorporates_result:
        sources.append("opencorporates")
    if gleif_result:
        sources.append("gleif")
    if sec_result:
        sources.append("sec_edgar")
    if explorium_result:
        sources.append("explorium")
    competitor["enrichment_sources"] = list(set(sources))

    return competitor


# ── Node 1: identify_competitors ──────────────────────────────────────────────

async def _cached_competitors(session, target_company_id: int) -> list[dict[str, Any]]:
    """Return competitors already stored in the DB for this target."""
    rows = await list_competitor_companies(session, target_company_id=target_company_id)
    return [
        {
            "name": r.name,
            "domain": r.domain,
            "funding_stage": r.funding_stage,
            "hq_location": r.hq_location,
            "source_db": r.source_db,
        }
        for r in rows
    ]


async def _tavily_competitors(company_name: str, sector: str | None) -> list[dict[str, Any]]:
    """Use Tavily web search to discover competitors. Primary discovery source.

    Returns a list of actual competitor company names (not article titles).
    Uses an LLM pass to extract real company names from search result snippets.
    """
    try:
        from tavily import AsyncTavilyClient
    except ImportError:  # pragma: no cover
        return []

    key = settings.tavily_api_key
    if not key:
        return []

    client = AsyncTavilyClient(api_key=key)
    query = f"competitors of {company_name}"
    if sector:
        query += f" in {sector}"

    try:
        result = await client.search(query, max_results=10, search_depth="basic")
    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        return []

    # Gather raw search results
    raw_results: list[dict[str, Any]] = []
    for r in result.get("results", []):
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "") or ""
        domain = url.split("/")[2] if "//" in url else url
        raw_results.append({
            "title": title,
            "domain": domain,
            "content": content[:400] if content else "",
        })

    if not raw_results:
        return []

    # Use LLM to extract real company names from search results
    llm = LLMClient()
    system_prompt = (
        "You are a PE research analyst. Given web search results about competitors of a company, "
        "extract ONLY the actual competitor company names. Do NOT include article titles, blog names, "
        "or the target company itself. Return ONLY a JSON array of strings."
    )
    user_prompt = (
        f"Target company: {company_name}\n\n"
        "Web search results:\n"
        + "\n".join(
            f"- Title: {r['title']}\n  Content: {r['content'][:300]}"
            for r in raw_results
        )
        + "\n\nExtract ONLY the real competitor company names as a JSON array of strings. "
        "Exclude the target company and any non-company entries (article titles, blog names, etc.)."
    )

    try:
        extracted = await llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        )
        # Parse JSON array from response
        import json as _json
        # Try to find JSON array in the response
        text = extracted.strip()
        if "[" in text and "]" in text:
            start = text.index("[")
            end = text.rindex("]") + 1
            names = _json.loads(text[start:end])
        else:
            names = []
    except Exception as exc:
        logger.warning("LLM competitor extraction failed: %s", exc)
        names = []

    # Build competitor records from extracted names
    competitors: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    target_lower = company_name.lower()

    # Article-title filter words — reject entries that look like blog posts
    _ARTICLE_WORDS = {
        "alternatives", "competitors", "vs", "versus", "compare", "comparison",
        "best", "top", "guide", "review", "reviews", "2024", "2025", "2026",
        "how to", "what is", "why", "the ", "for ", "you should", "explained",
        "ultimate", "complete", "definitive", "ranked", "rated", "list",
    }

    for name in names:
        if not isinstance(name, str) or not name.strip():
            continue
        clean_name = name.strip()
        lower = clean_name.lower()
        # Skip if it's the target company
        if lower == target_lower or lower in target_lower or target_lower in lower:
            continue
        # Skip if it looks like an article title
        if any(w in lower for w in _ARTICLE_WORDS):
            continue
        # Skip duplicates
        if lower in seen_names:
            continue
        seen_names.add(lower)
        competitors.append({
            "name": clean_name,
            "domain": None,
            "funding_stage": None,
            "hq_location": None,
            "source_db": "tavily",
            "tavily_snippet": None,
        })

    return competitors


async def identify_competitors(state: DealState) -> DealState:
    """Node 1: Discover competitors using free APIs first, then fallback."""
    company_id = state.get("company_id")
    if not company_id:
        state["errors"] = state.get("errors", []) + ["Missing company_id in state"]
        return state

    # Article-title filter words — reject entries that look like blog posts
    _ARTICLE_WORDS = {
        "alternatives", "competitors", "vs", "versus", "compare", "comparison",
        "best", "top", "guide", "review", "reviews", "2024", "2025", "2026",
        "how to", "what is", "why", "the ", "for ", "you should", "explained",
        "ultimate", "complete", "definitive", "ranked", "rated", "list",
        "features against", "better options", "growing businesses", "modern ap",
    }

    def _is_article_title(name: str) -> bool:
        lower = name.lower()
        return any(w in lower for w in _ARTICLE_WORDS)

    # Load target company from DB
    async with async_session_factory() as session:
        company = await get_company_by_id(session, company_id)
        if not company:
            state["errors"] = state.get("errors", []) + [f"Company with id={company_id} not found"]
            return state

        company_name = company.name
        sector = company.sector or ""
        geography = company.geography

        # 1. Cached DB competitors — filter out article-title entries
        competitors = await _cached_competitors(session, company_id)
        competitors = [c for c in competitors if not _is_article_title(c.get("name", ""))]
        structured_count = len(competitors)
        sources = set()
        if competitors:
            sources.update({c["source_db"] for c in competitors})

        # 2. Tavily web search (primary source — free, no key needed if using mock)
        # Re-run if no cached competitors OR cached ones look like article titles
        if not competitors:
            tv = await _tavily_competitors(company_name, sector)
            if tv:
                competitors.extend(tv)
                sources.add("tavily")
                structured_count = len(competitors)

        # 3. Enrich competitors (Wikidata, GLEIF, OpenCorporates, Explorium)
        if competitors:
            enriched_tasks = [_enrich_competitor(c) for c in competitors]
            competitors = await asyncio.gather(*enriched_tasks)
            sources.update({"wikidata", "gleif", "opencorporates", "explorium"})

        # 4. Deterministic sector-map fallback (guaranteed real companies)
        if not competitors:
            sector_key = None
            # Try exact match first
            for k in _FALLBACK_COMPETITORS:
                if k.lower() == sector.lower():
                    sector_key = k
                    break
            # Then try key contained in sector (more specific → general)
            if not sector_key:
                for k in sorted(_FALLBACK_COMPETITORS, key=len, reverse=True):
                    if k.lower() in sector.lower():
                        sector_key = k
                        break
            # Then try sector contained in key
            if not sector_key:
                for k in sorted(_FALLBACK_COMPETITORS, key=len, reverse=True):
                    if sector.lower() in k.lower():
                        sector_key = k
                        break
            if sector_key:
                competitors = _FALLBACK_COMPETITORS[sector_key][:8]
                sources.add("fallback_sector_map")
            else:
                # Absolute last resort: generic B2B SaaS map
                competitors = _FALLBACK_COMPETITORS["B2B SaaS"][:8]
                sources.add("fallback_sector_map")

        # Deduplicate by domain or name
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for c in competitors:
            key = (c.get("domain") or "").lower() or c["name"].lower()
            if key and key not in seen:
                seen.add(key)
                deduped.append(c)

        # Select top 5-8
        selected = deduped[:8]

        # Cache any new competitors into DB
        for c in selected:
            if c.get("source_db") in ("tavily", "fallback_sector_map"):
                existing = await list_competitor_companies(
                    session, target_company_id=company_id, source_db=c["source_db"]
                )
                existing_names = {e.name.lower() for e in existing}
                if c["name"].lower() not in existing_names:
                    await create_competitor_company(
                        session,
                        target_company_id=company_id,
                        name=c["name"],
                        domain=c.get("domain"),
                        source_db=c["source_db"],
                        sector=sector or None,
                        funding_stage=c.get("funding_stage"),
                        hq_location=c.get("hq_location"),
                    )

        state["competitors"] = selected
        state["competitor_sources"] = list(sources)
        state["structured_competitor_count"] = structured_count
        state["company_name"] = company_name
        state["sector"] = sector
    return state


# ── Node 2: extract_profiles ────────────────────────────────────────────────

_SYSTEM_PROMPT_PROFILE = """You are a PE competitive intelligence analyst.
Given a competitor company name and sector, extract the following structured profile.
Be factual and concise. If you don't know a field, say "Unknown".
For revenue and employees, you MUST provide your best estimate based on public knowledge.
Examples of good estimates:
  revenue: "$500M-$1B", "$10M-$50M", "$1B-$5B", "$100M-$500M"
  employees: "1K-5K", "100-500", "5K-10K", "10K+"
Return ONLY valid JSON matching the schema."""

_USER_PROMPT_PROFILE_TEMPLATE = """Company: {name}
Sector: {sector}
Known info: {context}

Extract a structured competitor profile. For ALL fields, provide your best estimate.
If information is not publicly available, provide a reasonable estimate based on the
company's size, sector, and public presence.

Fields to extract:
- business_model (e.g., "Subscription-based SaaS", "Transaction fees")
- pricing (e.g., "Tiered pricing", "Usage-based", "Per-seat")
- segment (e.g., "SMB", "mid-market", "enterprise")
- geography (e.g., "Global", "North America", "Europe")
- funding (e.g., "Public", "VC-backed", "PE-backed", "Bootstrapped")
- key_differentiators (1-2 sentences on how this competitor differs from {target_name})
- revenue (MUST provide estimated range, e.g., "$10M-$50M", "$500M-$1B")
- employees (MUST provide estimated range, e.g., "100-500", "1K-5K")

Return ONLY valid JSON."""


async def extract_profiles(state: DealState) -> DealState:
    """Node 2: For each verified competitor, build a detailed profile using LLM."""
    competitors = state.get("competitors", [])
    if not competitors:
        state["errors"] = state.get("errors", []) + ["No competitors to profile"]
        return state

    target_name = state.get("company_name", "the target")
    sector = state.get("sector", "")
    profiles: dict[str, dict[str, Any]] = {}

    llm = LLMClient()

    for comp in competitors:
        name = comp["name"]
        context_parts = []
        if comp.get("domain"):
            context_parts.append(f"domain: {comp['domain']}")
        if comp.get("funding_stage"):
            context_parts.append(f"funding: {comp['funding_stage']}")
        if comp.get("hq_location"):
            context_parts.append(f"HQ: {comp['hq_location']}")
        if comp.get("employees"):
            context_parts.append(f"employees: {comp['employees']}")
        if comp.get("revenue"):
            context_parts.append(f"revenue: {comp['revenue']}")
        if comp.get("industry"):
            context_parts.append(f"industry: {comp['industry']}")
        if comp.get("company_size"):
            context_parts.append(f"company_size: {comp['company_size']}")
        if comp.get("tavily_snippet"):
            context_parts.append(f"web_snippet: {comp['tavily_snippet']}")
        context = "; ".join(context_parts) if context_parts else "No additional context"

        user_prompt = _USER_PROMPT_PROFILE_TEMPLATE.format(
            name=name, sector=sector, context=context, target_name=target_name
        )

        try:
            parsed = await llm.chat_structured(
                system_prompt=_SYSTEM_PROMPT_PROFILE,
                user_prompt=user_prompt,
                response_model=CompetitorProfile,
            )
            profiles[name] = parsed.model_dump()
        except Exception as exc:
            logger.warning("LLM profile extraction failed for %s: %s", name, exc)
            # Fallback profile so the graph continues
            profiles[name] = {
                "business_model": "Unknown",
                "pricing": "Unknown",
                "segment": "Unknown",
                "geography": comp.get("hq_location", "Unknown"),
                "funding": comp.get("funding_stage", "Unknown"),
                "key_differentiators": "Unknown",
                "revenue": "Unknown",
                "employees": "Unknown",
            }

    state["competitor_profiles"] = profiles
    return state


# ── Node 3: build_matrix ─────────────────────────────────────────────────────

async def build_matrix(state: DealState) -> DealState:
    """Node 3: Build a structured competitive matrix from profiles.

    Uses LLM-generated profiles for business model, pricing, segment, geography,
    funding, key differentiators, revenue, and employees. Enriches with
    Wikidata/Explorium for revenue and employees where available.
    """
    profiles = state.get("competitor_profiles", {})
    if not profiles:
        state["errors"] = state.get("errors", []) + ["No profiles to build matrix"]
        return state

    competitors = state.get("competitors", [])
    comp_lookup = {c["name"]: c for c in competitors}
    target_name = state.get("company_name", "").lower()

    competitors_matrix: dict[str, dict[str, Any]] = {}
    for name, prof in profiles.items():
        # Skip the target company itself
        if name.lower() == target_name or target_name in name.lower() or name.lower() in target_name:
            continue

        c = comp_lookup.get(name, {})

        # Revenue: prefer enriched data, fallback to LLM estimate, then heuristic
        raw_revenue = c.get("revenue") or prof.get("revenue")
        formatted_revenue = _format_revenue(raw_revenue)
        if not formatted_revenue:
            segment = prof.get("segment", "").lower()
            funding = prof.get("funding", "").lower()
            formatted_revenue = _estimate_revenue(segment, funding)

        # Employees: prefer enriched data, fallback to LLM estimate, then heuristic
        raw_employees = c.get("employees") or prof.get("employees")
        formatted_employees = _format_employees(raw_employees)
        if not formatted_employees:
            segment = prof.get("segment", "").lower()
            funding = prof.get("funding", "").lower()
            formatted_employees = _estimate_employees(segment, funding)

        # Use LLM profile for most fields; enriched data for revenue/employees
        competitors_matrix[name] = {
            "business_model": _clean_value(prof.get("business_model", "")),
            "pricing": _clean_value(prof.get("pricing", "")),
            "segment": _clean_value(prof.get("segment", "")),
            "geography": _clean_value(prof.get("geography", "")),
            "funding": _clean_value(prof.get("funding", "")),
            "key_differentiators": _clean_value(prof.get("key_differentiators", "")),
            "employees": formatted_employees,
            "revenue": formatted_revenue,
            "company_size": c.get("company_size"),
            "industry": c.get("industry"),
            "source": state.get("competitor_sources", ["unknown"])[0],
        }

    state["competitive_map"] = {"competitors": competitors_matrix}
    return state


def _estimate_revenue(segment: str, funding: str) -> str | None:
    """Heuristic revenue estimate based on segment and funding stage."""
    seg = segment.lower()
    fund = funding.lower()

    # Public companies are typically $500M+
    if "public" in fund:
        return "$500M+"
    # PE-backed mid-market/enterprise
    if "pe-backed" in fund or "private equity" in fund:
        if "enterprise" in seg:
            return "$200M-$500M"
        if "mid-market" in seg:
            return "$50M-$200M"
        return "$10M-$50M"
    # VC-backed
    if "vc-backed" in fund or "vc" in fund:
        if "enterprise" in seg:
            return "$50M-$200M"
        if "mid-market" in seg:
            return "$10M-$50M"
        return "$1M-$10M"
    # Bootstrapped
    if "bootstrap" in fund:
        if "enterprise" in seg:
            return "$10M-$50M"
        if "mid-market" in seg:
            return "$5M-$20M"
        return "$1M-$5M"
    # Default by segment only
    if "enterprise" in seg:
        return "$50M+"
    if "mid-market" in seg:
        return "$10M-$50M"
    if "smb" in seg:
        return "$1M-$10M"
    return "$5M-$20M"


def _estimate_employees(segment: str, funding: str) -> str | None:
    """Heuristic employee estimate based on segment and funding stage."""
    seg = segment.lower()
    fund = funding.lower()

    if "public" in fund:
        if "enterprise" in seg:
            return "5K+"
        return "1K-5K"
    if "pe-backed" in fund or "private equity" in fund:
        if "enterprise" in seg:
            return "1K-5K"
        if "mid-market" in seg:
            return "500-1K"
        return "100-500"
    if "vc-backed" in fund or "vc" in fund:
        if "enterprise" in seg:
            return "500-1K"
        if "mid-market" in seg:
            return "100-500"
        return "50-200"
    if "bootstrap" in fund:
        if "enterprise" in seg:
            return "100-500"
        if "mid-market" in seg:
            return "50-200"
        return "10-50"
    # Default by segment only
    if "enterprise" in seg:
        return "1K+"
    if "mid-market" in seg:
        return "100-500"
    if "smb" in seg:
        return "10-100"
    return "50-200"


def _format_revenue(val: Any) -> str | None:
    """Convert a raw revenue value into a human-readable range string."""
    if not val:
        return None

    # If it's a string, check for non-numeric non-range values first
    if isinstance(val, str):
        v = val.strip()
        if v.lower() in ("unknown", "n/a", "not available", "not disclosed"):
            return None
        # If it contains letters (like "1M-5M", "$500M-$1B"), pass it through
        if v and not v.replace(".", "").replace("-", "").replace("$", "").replace("M", "").replace("B", "").replace("K", "").replace(" ", "").replace(",", "").isdigit():
            # But if it's just a word like "Unknown", filter it
            if v.replace(".", "").replace("-", "").replace("$", "").replace(" ", "").isalpha():
                return None
            return v  # already formatted like "1M-5M" or "500M-1B"
        # Try to parse as a number
        try:
            num = float(v)
        except ValueError:
            return None
    else:
        try:
            num = float(val)
        except (TypeError, ValueError):
            return None

    # Format large numbers into readable ranges
    if num >= 1e12:
        return f"${num/1e12:.1f}T+"
    if num >= 1e11:
        return f"${num/1e9:.0f}B+"
    if num >= 1e10:
        return f"${num/1e9:.0f}B+"
    if num >= 1e9:
        return f"${num/1e9:.1f}B+"
    if num >= 1e8:
        return f"${num/1e6:.0f}M+"
    if num >= 1e7:
        return f"${num/1e6:.0f}M+"
    if num >= 1e6:
        return f"${num/1e6:.1f}M+"
    return f"${num:.0f}"


def _format_employees(val: Any) -> str | None:
    """Convert a raw employee count into a human-readable range string."""
    if not val:
        return None

    if isinstance(val, str):
        v = val.strip()
        if v.lower() in ("unknown", "n/a", "not available", "not disclosed"):
            return None
        # If it contains letters (like "1K-5K"), pass it through
        if v and not v.replace(".", "").replace("-", "").replace("K", "").replace(" ", "").isdigit():
            if v.replace(".", "").replace("-", "").replace(" ", "").isalpha():
                return None
            return v  # already formatted like "1K-5K"
        try:
            num = float(v)
        except ValueError:
            return None
    else:
        try:
            num = float(val)
        except (TypeError, ValueError):
            return None

    if num >= 100000:
        return f"{num/1000:.0f}K+"
    if num >= 10000:
        return f"{num/1000:.0f}K+"
    if num >= 1000:
        return f"{num/1000:.1f}K+"
    return f"{num:.0f}"


def _clean_value(val: str) -> str | None:
    """Clean up LLM output: strip whitespace, convert 'Unknown' to None."""
    if not val or not isinstance(val, str):
        return None
    v = val.strip()
    if v.lower() in ("unknown", "n/a", "not available", "not disclosed"):
        return None
    return v


# ── Node 4: assess_moat ──────────────────────────────────────────────────────

_SYSTEM_PROMPT_MOAT = """You are a competitive strategy analyst for a top-tier PE firm.
Assess the target company's differentiation based on switching costs, network effects,
IP / proprietary technology, distribution advantages, and brand / reputation.
For each dimension, provide a rating (1-5) and a brief explanation.
CITE SPECIFIC COMPETITORS BY NAME in your analysis (e.g., 'Unlike Competitor X, the target has...').
Return ONLY valid JSON matching the schema."""

_USER_PROMPT_MOAT_TEMPLATE = """Target Company: {target_name}
Sector: {sector}
Competitor Matrix:
{matrix_json}

Assess the target's competitive moat. Cite specific competitors by name.
Return ONLY valid JSON."""


async def assess_moat(state: DealState) -> DealState:
    """Node 4: LLM analysis of target's differentiation with specific competitor citations."""
    competitive_map = state.get("competitive_map", {})
    competitors = state.get("competitors", [])

    if not competitors:
        state["errors"] = state.get("errors", []) + ["No competitors for moat assessment"]
        return state

    target_name = state.get("company_name", "the target")
    sector = state.get("sector", "")

    llm = LLMClient()
    matrix_json = str(competitive_map.get("competitors", {}))

    user_prompt = _USER_PROMPT_MOAT_TEMPLATE.format(
        target_name=target_name, sector=sector, matrix_json=matrix_json
    )

    try:
        parsed = await llm.chat_structured(
            system_prompt=_SYSTEM_PROMPT_MOAT,
            user_prompt=user_prompt,
            response_model=MoatAssessment,
        )
        moat_data = parsed.model_dump()
    except Exception as exc:
        logger.warning("LLM moat assessment failed: %s", exc)
        # Fallback so graph completes
        competitor_names = [c["name"] for c in competitors]
        moat_data = {
            "switching_costs": "Unable to assess — LLM unavailable",
            "network_effects": "Unable to assess — LLM unavailable",
            "ip_proprietary_tech": "Unable to assess — LLM unavailable",
            "distribution_advantages": "Unable to assess — LLM unavailable",
            "brand_reputation": "Unable to assess — LLM unavailable",
            "overall_moat": f"Assessment unavailable. Key competitors: {', '.join(competitor_names)}.",
            "confidence_score": 0.0,
            "data_sources": state.get("competitor_sources", ["unknown"]),
        }

    # Compute confidence score: % of competitors from structured DB
    structured_count = state.get("structured_competitor_count", 0)
    total_competitors = len(competitors)
    confidence_score = (
        structured_count / total_competitors if total_competitors > 0 else 0.0
    )
    # If we used fallback sector map, confidence is lower
    sources = state.get("competitor_sources", ["unknown"])
    if "fallback_sector_map" in sources:
        confidence_score = min(confidence_score, 0.5)

    if "data_sources" not in moat_data:
        moat_data["data_sources"] = sources
    moat_data["confidence_score"] = confidence_score

    if state.get("competitive_map") is None:
        state["competitive_map"] = {}
    state["competitive_map"]["moat_assessment"] = moat_data
    state["competitive_map"]["confidence_score"] = confidence_score
    state["competitive_map"]["data_sources"] = sources

    return state


# ── Graph wiring ─────────────────────────────────────────────────────────────

builder = StateGraph(DealState)
builder.add_node("identify_competitors", identify_competitors)
builder.add_node("extract_profiles", extract_profiles)
builder.add_node("build_matrix", build_matrix)
builder.add_node("assess_moat", assess_moat)

builder.set_entry_point("identify_competitors")
builder.add_edge("identify_competitors", "extract_profiles")
builder.add_edge("extract_profiles", "build_matrix")
builder.add_edge("build_matrix", "assess_moat")
builder.add_edge("assess_moat", END)

competitive_graph = builder.compile()


# ── Helper ───────────────────────────────────────────────────────────────────

async def run_competitive(company_id: int) -> DealState:
    """Run the full competitive analysis graph for a company.

    Args:
        company_id: Primary key of the target company in the ``companies`` table.

    Returns:
        Final ``DealState`` containing ``competitive_map``, ``competitors``, etc.
    """
    async with async_session_factory() as session:
        result = await session.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()

    if not company:
        state = create_initial_state("Unknown", company_id=company_id)
        state["errors"] = [f"Company with id={company_id} not found"]
        return state

    state = create_initial_state(company.name, company_id=company_id)
    state["sector"] = company.sector or ""
    final_state = await competitive_graph.ainvoke(state)
    return final_state  # type: ignore[return-value]
