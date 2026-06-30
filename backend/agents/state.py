"""Shared state definitions for the LangGraph deal pipeline."""

from __future__ import annotations

import json
import uuid
from typing import TypedDict

from schemas.financials import FinancialProfile


class LBOResult(TypedDict, total=False):
    """LBO model output stored in pipeline state."""

    entry_equity: float | None
    entry_debt: float | None
    irr: float | None
    moic: float | None
    exit_ev: float | None
    exit_equity: float | None


class DealState(TypedDict, total=False):
    """Shared state across all deal-pipeline agents."""

    company_name: str
    company_id: int | None
    sector: str | None
    gics_sector: str | None
    gics_industry_group: str | None
    financials: FinancialProfile | None
    competitive_map: dict | None
    competitors: list[dict] | None
    competitor_profiles: dict | None
    competitor_sources: list[str] | None
    structured_competitor_count: int | None
    lbo_result: LBOResult | None
    lbo_scenarios: dict | None
    lbo_results: dict | None
    lbo_sensitivity: dict | None
    lbo_interpretation: str | None
    overrides: dict | None
    memo_context: dict | None
    memo_sections: dict | None
    memo_edit_notes: dict | None
    memo_total_words: int | None
    memo_avg_confidence: float | None
    memo_id: int | None
    filing_research: list[dict] | None
    web_research: list[dict] | None
    research: dict | None
    run_id: str
    errors: list[str]
    risk_flags: list[str]
    interpretation: str | None
    thesis: str | None
    sourcing_filters: dict | None
    candidates: list[dict] | None
    ranked_candidates: list[dict] | None


def create_initial_state(company_name: str, company_id: int | None = None) -> DealState:
    """Create a fresh DealState with sensible defaults."""
    return {
        "company_name": company_name,
        "company_id": company_id,
        "sector": None,
        "financials": None,
        "competitive_map": None,
        "lbo_result": None,
        "lbo_scenarios": None,
        "lbo_results": None,
        "lbo_sensitivity": None,
        "lbo_interpretation": None,
        "overrides": None,
        "memo_context": None,
        "memo_sections": None,
        "memo_edit_notes": None,
        "memo_total_words": None,
        "memo_avg_confidence": None,
        "memo_id": None,
        "thesis": None,
        "sourcing_filters": None,
        "candidates": None,
        "ranked_candidates": None,
        "run_id": str(uuid.uuid4()),
        "errors": [],
    }


def _deal_state_encoder(obj: object) -> object:
    """Custom JSON encoder helper for DealState objects."""
    import dataclasses as _dc

    if isinstance(obj, FinancialProfile):
        return obj.model_dump(mode="json")
    if _dc.is_dataclass(obj) and not isinstance(obj, type):
        return _dc.asdict(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def deal_state_to_json(state: DealState) -> str:
    """Serialize a DealState to a JSON string."""
    return json.dumps(state, default=_deal_state_encoder)


def deal_state_from_json(data: str) -> DealState:
    """Deserialize a JSON string back to a DealState."""
    parsed = json.loads(data)
    if parsed.get("financials") is not None:
        parsed["financials"] = FinancialProfile(**parsed["financials"])
    if parsed.get("lbo_result") is not None:
        parsed["lbo_result"] = LBOResult(**parsed["lbo_result"])
    return parsed  # type: ignore[return-value]
