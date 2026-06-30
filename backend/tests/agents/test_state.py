"""Tests for the LangGraph deal pipeline state."""

from __future__ import annotations

import json
from typing import Any

import pytest

from agents.state import (
    DealState,
    LBOResult,
    create_initial_state,
    deal_state_from_json,
    deal_state_to_json,
)
from schemas.financials import FinancialProfile


class TestCreateInitialState:
    def test_returns_all_keys(self) -> None:
        state = create_initial_state("Acme Corp", company_id=42)
        expected_keys = {
            "company_name",
            "company_id",
            "sector",
            "financials",
            "competitive_map",
            "lbo_result",
            "lbo_scenarios",
            "lbo_results",
            "lbo_sensitivity",
            "lbo_interpretation",
            "overrides",
            "memo_context",
            "memo_sections",
            "memo_edit_notes",
            "memo_total_words",
            "memo_avg_confidence",
            "memo_id",
            "run_id",
            "errors",
            "thesis",
            "sourcing_filters",
            "candidates",
            "ranked_candidates",
        }
        assert set(state.keys()) == expected_keys

    def test_company_name_set(self) -> None:
        state = create_initial_state("Acme Corp")
        assert state["company_name"] == "Acme Corp"

    def test_company_id_optional(self) -> None:
        state = create_initial_state("Acme Corp")
        assert state["company_id"] is None

        state_with_id = create_initial_state("Acme Corp", company_id=42)
        assert state_with_id["company_id"] == 42

    def test_defaults_are_none_or_empty(self) -> None:
        state = create_initial_state("Acme Corp")
        assert state["sector"] is None
        assert state["financials"] is None
        assert state["competitive_map"] is None
        assert state["lbo_result"] is None
        assert state["memo_sections"] is None
        assert state["errors"] == []

    def test_run_id_is_uuid(self) -> None:
        state = create_initial_state("Acme Corp")
        assert isinstance(state["run_id"], str)
        assert len(state["run_id"]) > 0


class TestDealStateSerialization:
    def test_round_trip_with_none_values(self) -> None:
        original = create_initial_state("Acme Corp", company_id=1)
        json_str = deal_state_to_json(original)
        restored = deal_state_from_json(json_str)
        assert restored["company_name"] == original["company_name"]
        assert restored["company_id"] == original["company_id"]
        assert restored["sector"] is None
        assert restored["financials"] is None
        assert restored["run_id"] == original["run_id"]
        assert restored["errors"] == []

    def test_round_trip_with_financials(self) -> None:
        original = create_initial_state("Acme Corp")
        original["financials"] = FinancialProfile(
            revenue=100.0,
            ebitda=20.0,
            ebitda_margin=0.20,
            revenue_growth=0.10,
            net_debt=30.0,
            net_debt_ebitda=1.5,
            fcf=15.0,
            fcf_yield=0.15,
        )
        json_str = deal_state_to_json(original)
        restored = deal_state_from_json(json_str)
        assert restored["financials"] is not None
        assert restored["financials"].revenue == 100.0
        assert restored["financials"].ebitda == 20.0

    def test_round_trip_with_lbo_result(self) -> None:
        original = create_initial_state("Acme Corp")
        original["lbo_result"] = LBOResult(
            entry_equity=70.0,
            entry_debt=30.0,
            irr=0.25,
            moic=2.5,
            exit_ev=250.0,
            exit_equity=175.0,
        )
        json_str = deal_state_to_json(original)
        restored = deal_state_from_json(json_str)
        assert restored["lbo_result"] is not None
        assert restored["lbo_result"]["irr"] == 0.25
        assert restored["lbo_result"]["moic"] == 2.5

    def test_round_trip_with_memo_sections(self) -> None:
        original = create_initial_state("Acme Corp")
        original["memo_sections"] = {
            "Executive Summary": {
                "content": "Summary text.",
                "word_count": 2,
                "confidence_score": 0.90,
            }
        }
        json_str = deal_state_to_json(original)
        restored = deal_state_from_json(json_str)
        assert restored["memo_sections"] == original["memo_sections"]


class TestPostgreSQLJSONB:
    """Simulate JSONB round-trip via json.dumps / json.loads."""

    def test_jsonb_round_trip(self) -> None:
        state = create_initial_state("Acme Corp", company_id=1)
        state["financials"] = FinancialProfile(
            revenue=100.0,
            ebitda=20.0,
            ebitda_margin=0.20,
            revenue_growth=0.10,
            net_debt=30.0,
            net_debt_ebitda=1.5,
            fcf=15.0,
            fcf_yield=0.15,
        )
        state["lbo_result"] = LBOResult(
            entry_equity=70.0,
            entry_debt=30.0,
            irr=0.25,
            moic=2.5,
            exit_ev=250.0,
            exit_equity=175.0,
        )
        state["memo_sections"] = {
            "Executive Summary": {
                "content": "Summary text.",
                "word_count": 2,
                "confidence_score": 0.90,
            }
        }
        # Simulate PostgreSQL JSONB storage: JSON string
        jsonb_str = deal_state_to_json(state)
        restored = deal_state_from_json(jsonb_str)
        assert restored["company_name"] == "Acme Corp"
        assert restored["company_id"] == 1
        assert restored["financials"] is not None
        assert restored["financials"].revenue == 100.0
        assert restored["lbo_result"] is not None
        assert restored["lbo_result"]["moic"] == 2.5
        assert restored["memo_sections"]["Executive Summary"]["confidence_score"] == 0.90

    def test_jsonb_empty_state(self) -> None:
        state = create_initial_state("Empty Corp")
        jsonb_str = deal_state_to_json(state)
        restored = deal_state_from_json(jsonb_str)
        assert restored["company_name"] == "Empty Corp"
        assert restored["financials"] is None
        assert restored["errors"] == []
