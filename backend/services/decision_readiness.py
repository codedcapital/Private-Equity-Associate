"""Decision Readiness — Stage-aware readiness calculation.

Determines whether a deal is ready for the next stage by checking:
1. Required evidence modules are VERIFIED (or at least not UNKNOWN)
2. Required diligence items are COMPLETE
3. No BLOCKER items are outstanding

Returns a readiness score (0-100) and a checklist of met/unmet requirements.
"""

from __future__ import annotations

import logging
from typing import Any

from db.crud import (
    get_latest_confidence_ledger,
    list_diligence_items,
    list_investment_views,
)
from db.models import DiligenceItem, DiligenceStatus, EvidenceStatus
from db.session import async_session_factory

logger = logging.getLogger(__name__)


# ── Stage requirements ───────────────────────────────────────────────────────

STAGE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "screening": {
        "required_modules": ["financial"],
        "required_diligence": [],
        "description": "Can we spend time on this?",
    },
    "initial_diligence": {
        "required_modules": ["financial", "competitive"],
        "required_diligence": ["customer_calls_sample"],
        "description": "Can we build a model?",
    },
    "deep_diligence": {
        "required_modules": ["financial", "competitive", "research", "market"],
        "required_diligence": ["management_interview", "legal_review"],
        "description": "Can we go to IC?",
    },
    "pre_ic": {
        "required_modules": ["financial", "competitive", "research", "market", "valuation"],
        "required_diligence": ["all_blocker_complete"],
        "description": "Is the pack ready?",
    },
}


def _evidence_status_to_weight(status: EvidenceStatus) -> float:
    """Convert evidence status to a readiness weight."""
    weights = {
        EvidenceStatus.VERIFIED: 1.0,
        EvidenceStatus.NEEDS_VALIDATION: 0.7,
        EvidenceStatus.CONFLICTING: 0.3,
        EvidenceStatus.UNKNOWN: 0.0,
    }
    return weights.get(status, 0.0)


class DecisionReadiness:
    """Computes decision readiness for a deal at its current stage."""

    def __init__(self, deal_id: int, current_stage: str):
        self.deal_id = deal_id
        self.current_stage = current_stage

    async def compute(self) -> dict[str, Any]:
        """Compute the readiness score and checklist for the current stage.

        Returns:
            {
                "score": int (0-100),
                "current_stage": str,
                "met": list[str],
                "unmet": list[str],
                "recommended_next_step": str,
                "next_stage": str | None,
            }
        """
        async with async_session_factory() as session:
            # 1. Get latest investment view
            views = await list_investment_views(session, self.deal_id)
            latest_view = views[0] if views else None

            # 2. Get all diligence items
            diligence_items = await list_diligence_items(session, deal_id=self.deal_id)

            # 3. Get latest confidence ledger
            ledger = await get_latest_confidence_ledger(session, self.deal_id)

            # 4. Build requirements checklist
            requirements = STAGE_REQUIREMENTS.get(self.current_stage, {})
            required_modules = requirements.get("required_modules", [])
            required_diligence = requirements.get("required_diligence", [])

            met: list[str] = []
            unmet: list[str] = []
            module_score = 0.0
            module_total = 0.0

            # Check evidence modules from ledger
            if ledger and ledger.factors:
                factor_statuses = {k: v.get("status", "UNKNOWN") for k, v in ledger.factors.items()}
                for module in required_modules:
                    module_total += 1.0
                    # Map module to factor status
                    status_str = factor_statuses.get(module, "UNKNOWN")
                    try:
                        status = EvidenceStatus(status_str.lower())
                    except ValueError:
                        status = EvidenceStatus.UNKNOWN
                    weight = _evidence_status_to_weight(status)
                    module_score += weight
                    if status == EvidenceStatus.VERIFIED:
                        met.append(f"{module.capitalize()} evidence verified")
                    elif status == EvidenceStatus.NEEDS_VALIDATION:
                        met.append(f"{module.capitalize()} evidence available (needs validation)")
                    elif status == EvidenceStatus.CONFLICTING:
                        unmet.append(f"{module.capitalize()} evidence has conflicts")
                    else:
                        unmet.append(f"{module.capitalize()} evidence missing")
            else:
                for module in required_modules:
                    module_total += 1.0
                    unmet.append(f"{module.capitalize()} evidence missing")

            # Check diligence items
            blocker_count = sum(
                1 for d in diligence_items if d.priority == "blocker" and d.status != "complete"
            )
            open_count = sum(1 for d in diligence_items if d.status != "complete")
            complete_count = len(diligence_items) - open_count

            for req in required_diligence:
                if req == "all_blocker_complete":
                    if blocker_count == 0:
                        met.append("All blocker diligence items complete")
                    else:
                        unmet.append(f"{blocker_count} blocker diligence item(s) outstanding")
                elif req == "management_interview":
                    has_mgmt = any(
                        "management" in d.title.lower() or "management" in d.category.lower()
                        for d in diligence_items
                    )
                    if has_mgmt:
                        met.append("Management interview scheduled or complete")
                    else:
                        unmet.append("Management interview not yet scheduled")
                elif req == "legal_review":
                    has_legal = any(
                        "legal" in d.title.lower() or "legal" in d.category.lower()
                        for d in diligence_items
                    )
                    if has_legal:
                        met.append("Legal review scheduled or complete")
                    else:
                        unmet.append("Legal review not yet scheduled")
                elif req == "customer_calls_sample":
                    has_customer = sum(
                        1 for d in diligence_items
                        if "customer" in d.title.lower() or "customer" in d.category.lower()
                    )
                    if has_customer >= 3:
                        met.append("Customer reference calls (3+) scheduled or complete")
                    else:
                        unmet.append(f"Customer reference calls ({has_customer}/3) — more needed")
                else:
                    unmet.append(f"Diligence requirement: {req}")

            # 5. Compute score
            total_checks = len(met) + len(unmet)
            if total_checks == 0:
                score = 0
            else:
                score = int((len(met) / total_checks) * 100)
            # Adjust by module readiness
            if module_total > 0:
                module_pct = module_score / module_total
                score = int((score * 0.5) + (module_pct * 100 * 0.5))

            # 6. Determine next stage and recommended step
            next_stage = None
            recommended_next_step = "Continue gathering evidence"
            stages = list(STAGE_REQUIREMENTS.keys())
            if self.current_stage in stages:
                idx = stages.index(self.current_stage)
                if score >= 80 and idx < len(stages) - 1:
                    next_stage = stages[idx + 1]
                    recommended_next_step = f"Ready to proceed to {next_stage.replace('_', ' ').title()}"
                elif score >= 50:
                    recommended_next_step = "Proceed with remaining open items"
                else:
                    recommended_next_step = "Resolve outstanding gaps before proceeding"

            return {
                "score": score,
                "current_stage": self.current_stage,
                "met": met,
                "unmet": unmet,
                "recommended_next_step": recommended_next_step,
                "next_stage": next_stage,
                "diligence_summary": {
                    "total": len(diligence_items),
                    "complete": complete_count,
                    "open": open_count,
                    "blockers": blocker_count,
                },
            }

    async def next_actions(self) -> list[dict[str, Any]]:
        """Generate recommended next actions based on readiness gaps."""
        readiness = await self.compute()
        actions = []
        for unmet in readiness["unmet"]:
            if "evidence missing" in unmet.lower():
                actions.append({
                    "action": f"Run evidence module for: {unmet}",
                    "priority": "HIGH",
                    "rationale": "Required evidence is not yet available",
                })
            elif "conflict" in unmet.lower():
                actions.append({
                    "action": f"Resolve evidence conflict: {unmet}",
                    "priority": "CRITICAL",
                    "rationale": "Conflicting evidence blocks progression",
                })
            elif "diligence" in unmet.lower() or "interview" in unmet.lower():
                actions.append({
                    "action": f"Complete diligence: {unmet}",
                    "priority": "HIGH",
                    "rationale": "Required diligence item is outstanding",
                })
            else:
                actions.append({
                    "action": f"Address: {unmet}",
                    "priority": "MEDIUM",
                    "rationale": "Required for stage progression",
                })
        return actions
