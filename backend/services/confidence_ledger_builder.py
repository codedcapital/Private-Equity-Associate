"""Confidence Ledger Builder — Transparent, auditable score breakdown.

Wraps the existing Decision Engine to produce a human-readable ledger
that explains exactly how the confidence score was computed and what
factors reduced it.

Usage:
    from services.confidence_ledger_builder import ConfidenceLedgerBuilder
    builder = ConfidenceLedgerBuilder(deal_id=7)
    ledger = await builder.build_from_modules(modules)
    # ledger is a ConfidenceLedger ORM object, persisted to DB
"""

from __future__ import annotations

import logging
from typing import Any

from db.crud import create_confidence_ledger, get_latest_confidence_ledger, list_diligence_items
from db.models import ConfidenceLedger, DiligenceItem, EvidenceStatus
from db.session import async_session_factory
from schemas.confidence_ledger import ConfidenceFactor
from schemas.evidence import DecisionOutput, EvidenceModule, ModuleScore

logger = logging.getLogger(__name__)


# ── Factor weights (must sum to 1.0) ─────────────────────────────────────────

FACTOR_WEIGHTS: dict[str, float] = {
    "Revenue Quality": 0.20,
    "Margin Stability": 0.15,
    "Customer Concentration": 0.15,
    "Management Quality": 0.20,
    "Exit Multiple": 0.15,
    "Leverage Capacity": 0.15,
}

# Map module types to factor names
MODULE_TO_FACTORS: dict[str, list[str]] = {
    "financial": ["Revenue Quality", "Margin Stability", "Leverage Capacity"],
    "research": ["Management Quality"],
    "competitive": ["Customer Concentration", "Exit Multiple"],
    "market": ["Exit Multiple"],
    "valuation": ["Exit Multiple"],
}


def _module_score_to_status(module_score: ModuleScore) -> str:
    """Map a module score to an evidence status string."""
    if module_score.warning_count > 0 and module_score.contradictory_count > 0:
        return "CONFLICTING"
    if module_score.score >= 80 and module_score.confidence >= 0.80:
        return "VERIFIED"
    if module_score.score >= 50 and module_score.confidence >= 0.50:
        return "NEEDS_VALIDATION"
    return "UNKNOWN"


class ConfidenceLedgerBuilder:
    """Builds a transparent confidence ledger from decision engine outputs."""

    def __init__(self, deal_id: int):
        self.deal_id = deal_id

    async def build_from_decision(
        self,
        decision: DecisionOutput,
        existing_diligence: list[DiligenceItem] | None = None,
    ) -> ConfidenceLedger:
        """Build a confidence ledger from a DecisionOutput.

        Args:
            decision: The DecisionOutput from the Decision Engine.
            existing_diligence: Optional list of diligence items for penalty calc.

        Returns:
            A persisted ConfidenceLedger record.
        """
        # 1. Base score from the decision engine's confidence_score
        base_score = int(decision.confidence_score * 100)

        # 2. Build factors from module scores
        factors: list[dict[str, Any]] = []
        for ms in decision.module_scores:
            factor_names = MODULE_TO_FACTORS.get(ms.module_type, [ms.module_type])
            for factor_name in factor_names:
                weight = FACTOR_WEIGHTS.get(factor_name, 0.15 / len(factor_names))
                status = _module_score_to_status(ms)
                contribution = int(ms.score * weight)
                penalty = 0
                if status == "CONFLICTING":
                    penalty = int(contribution * 0.5)
                    contribution = contribution - penalty
                elif status == "UNKNOWN":
                    penalty = contribution
                    contribution = 0

                factors.append(
                    {
                        "name": factor_name,
                        "weight": round(weight, 4),
                        "contribution": contribution,
                        "penalty": penalty,
                        "status": status,
                    }
                )

        # 3. Deduplicate factors by name (keep highest contribution)
        factor_by_name: dict[str, dict[str, Any]] = {}
        for f in factors:
            name = f["name"]
            if name not in factor_by_name or f["contribution"] > factor_by_name[name]["contribution"]:
                factor_by_name[name] = f
        unique_factors = list(factor_by_name.values())

        # 4. Apply diligence penalties
        diligence_penalties = []
        if existing_diligence:
            for item in existing_diligence:
                if item.status != "complete" and item.priority == "blocker":
                    penalty = -5
                    unique_factors.append(
                        {
                            "name": item.title,
                            "weight": 0.0,
                            "contribution": 0,
                            "penalty": penalty,
                            "status": "BLOCKER",
                        }
                    )
                    diligence_penalties.append(item.title)

        # 5. Compute final score
        final_score = base_score
        for f in unique_factors:
            final_score += f.get("contribution", 0)
            final_score += f.get("penalty", 0)
        final_score = max(0, min(100, final_score))

        # 6. Identify bottlenecks
        bottlenecks = [
            f["name"]
            for f in unique_factors
            if f["status"] in ("CONFLICTING", "UNKNOWN", "BLOCKER")
        ]

        # 7. Persist
        async with async_session_factory() as session:
            ledger = await create_confidence_ledger(
                session,
                deal_id=self.deal_id,
                base_score=base_score,
                factors={f["name"]: f for f in unique_factors},
                final_score=final_score,
                bottlenecks=bottlenecks,
            )
            return ledger

    async def build_from_modules(
        self,
        modules: list[EvidenceModule],
        existing_diligence: list[DiligenceItem] | None = None,
    ) -> ConfidenceLedger:
        """Build a ledger from raw EvidenceModules (uses the Decision Engine)."""
        from services.decision_engine import DecisionEngine

        engine = DecisionEngine(company_id=self.deal_id)
        decision = await engine.decide(modules, include_llm_synthesis=False)
        return await self.build_from_decision(decision, existing_diligence)

    async def get_latest(self) -> ConfidenceLedger | None:
        """Retrieve the latest confidence ledger for this deal."""
        async with async_session_factory() as session:
            return await get_latest_confidence_ledger(session, self.deal_id)

    @staticmethod
    def to_breakdown(ledger: ConfidenceLedger) -> dict[str, Any]:
        """Convert a ledger to a frontend-friendly breakdown."""
        factors = []
        for name, data in (ledger.factors or {}).items():
            factors.append(
                ConfidenceFactor(
                    name=name,
                    weight=data.get("weight", 0.0),
                    contribution=data.get("contribution"),
                    penalty=data.get("penalty"),
                    status=data.get("status", "UNKNOWN"),
                )
            )
        reduced_because = [
            f["name"]
            for f in (ledger.factors or {}).values()
            if f.get("penalty", 0) < 0 or f.get("status") in ("CONFLICTING", "UNKNOWN", "BLOCKER")
        ]
        return {
            "deal_id": ledger.deal_id,
            "final_score": ledger.final_score,
            "base_score": ledger.base_score,
            "factors": [f.model_dump() for f in factors],
            "bottlenecks": ledger.bottlenecks or [],
            "reduced_because": reduced_because,
        }
