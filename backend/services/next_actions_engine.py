"""Next Actions Engine — Proactive, contextual recommendations.

Two-tier approach:
1. Rule-based: Fast, deterministic checks for common gaps
2. LLM-based: Nuanced synthesis for complex situations

Caches results and only regenerates when deal state changes.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from db.crud import (
    get_latest_confidence_ledger,
    get_latest_investment_view,
    list_deal_events,
    list_diligence_items,
)
from db.models import DiligenceStatus, EvidenceStatus
from db.session import async_session_factory

logger = logging.getLogger(__name__)


# ── Cache (in-memory for MVP; Redis in production) ──────────────────────────

_next_action_cache: dict[str, dict[str, Any]] = {}


def _make_state_key(deal_id: int, state: dict) -> str:
    """Create a hash key from the current deal state."""
    canonical = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(f"{deal_id}:{canonical}".encode()).hexdigest()[:16]


def _get_cached(deal_id: int, state_key: str) -> list[dict] | None:
    key = f"{deal_id}:{state_key}"
    entry = _next_action_cache.get(key)
    if entry and entry["expires"] > datetime.now(timezone.utc):
        return entry["actions"]
    return None


def _set_cached(deal_id: int, state_key: str, actions: list[dict], ttl_minutes: int = 30) -> None:
    key = f"{deal_id}:{state_key}"
    _next_action_cache[key] = {
        "actions": actions,
        "expires": datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
    }


# ── Rule-Based Tier ──────────────────────────────────────────────────────────


class RuleBasedNextActions:
    """Fast, deterministic next actions from deal state."""

    def __init__(self, deal_id: int, stage: str):
        self.deal_id = deal_id
        self.stage = stage

    async def generate(self) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        async with async_session_factory() as session:
            # Load state
            diligence_items = await list_diligence_items(session, deal_id=self.deal_id)
            ledger = await get_latest_confidence_ledger(session, self.deal_id)
            view = await get_latest_investment_view(session, self.deal_id)
            events = await list_deal_events(session, deal_id=self.deal_id, limit=5)
            recent_conflicts = [e for e in events if "conflict" in e.description.lower()]

            # 1. Evidence conflicts
            if ledger and ledger.factors:
                for name, factor in ledger.factors.items():
                    if factor.get("status") == "CONFLICTING":
                        actions.append({
                            "id": f"resolve-conflict-{name}",
                            "title": f"Resolve evidence conflict: {name}",
                            "description": f"Conflicting evidence detected in {name}. Review and validate sources.",
                            "priority": "critical",
                            "category": "evidence",
                            "rationale": "Conflicting evidence blocks confidence progression and IC readiness.",
                        })

            # 2. Incomplete diligence at current stage
            not_started = [d for d in diligence_items if d.status == DiligenceStatus.NOT_STARTED.value]
            in_progress = [d for d in diligence_items if d.status == DiligenceStatus.IN_PROGRESS.value]
            blockers = [d for d in diligence_items if d.priority == "blocker" and d.status != "complete"]

            if blockers:
                actions.append({
                    "id": f"blocker-{blockers[0].id}",
                    "title": f"Complete blocker diligence: {blockers[0].title}",
                    "description": f"Blocker item '{blockers[0].title}' is outstanding and prevents stage progression.",
                    "priority": "critical",
                    "category": "diligence",
                    "rationale": "Blocker items must be resolved before the deal can advance.",
                })

            if self.stage == "initial_diligence" and not_started:
                customer_items = [d for d in not_started if "customer" in d.title.lower() or "customer" in d.category.lower()]
                if customer_items:
                    actions.append({
                        "id": f"customer-diligence-{customer_items[0].id}",
                        "title": f"Schedule customer reference calls — {len(customer_items)} remaining",
                        "description": f"Customer diligence item '{customer_items[0].title}' has not been started.",
                        "priority": "high",
                        "category": "diligence",
                        "rationale": "Customer validation is a required component of Initial Diligence.",
                    })

            if in_progress:
                actions.append({
                    "id": f"follow-up-{in_progress[0].id}",
                    "title": f"Follow up on diligence: {in_progress[0].title}",
                    "description": f"Diligence item '{in_progress[0].title}' is in progress — verify completion.",
                    "priority": "medium",
                    "category": "diligence",
                    "rationale": "In-progress items need attention to avoid pipeline stalls.",
                })

            # 3. Confidence below threshold for stage
            if ledger and ledger.final_score < 70 and self.stage in ("deep_diligence", "pre_ic"):
                actions.append({
                    "id": "confidence-below-threshold",
                    "title": "Confidence below threshold for stage — re-evaluate thesis",
                    "description": f"Current confidence score is {ledger.final_score}%. Required minimum for {self.stage} is 70%.",
                    "priority": "high",
                    "category": "confidence",
                    "rationale": "Confidence score insufficient for IC readiness. Gather additional evidence or refine thesis.",
                })

            # 4. No investment view yet
            if not view:
                actions.append({
                    "id": "create-investment-view",
                    "title": "Generate initial investment view",
                    "description": "No investment view exists. Run the intelligence pipeline to generate a draft.",
                    "priority": "high",
                    "category": "view",
                    "rationale": "An investment view is required to articulate the investment thesis.",
                })

            # 5. View is draft but not finalized
            if view and view.status == "draft" and self.stage == "pre_ic":
                actions.append({
                    "id": "finalize-view",
                    "title": "Finalize investment view for IC",
                    "description": f"View v{view.version} is still in DRAFT status. Mark as FINAL before IC presentation.",
                    "priority": "high",
                    "category": "view",
                    "rationale": "The investment view must be finalized before it can be presented to the Investment Committee.",
                })

            # 6. Evidence gaps (UNKNOWN status)
            if ledger and ledger.factors:
                unknown_factors = [name for name, f in ledger.factors.items() if f.get("status") == "UNKNOWN"]
                if unknown_factors:
                    actions.append({
                        "id": "gather-evidence",
                        "title": f"Gather evidence for {unknown_factors[0]}",
                        "description": f"No evidence available for '{unknown_factors[0]}'. Run the relevant module.",
                        "priority": "medium",
                        "category": "evidence",
                        "rationale": "Missing evidence creates uncertainty in the confidence score.",
                    })

        return actions


# ── LLM-Based Tier ───────────────────────────────────────────────────────────


class LLMNextActions:
    """Nuanced, LLM-generated next actions for complex situations."""

    def __init__(self, deal_id: int, stage: str):
        self.deal_id = deal_id
        self.stage = stage

    async def generate(self) -> dict[str, Any] | None:
        """Generate a single, high-quality next action via LLM.

        Returns:
            A single action dict with action, rationale, priority.
            None if the LLM call fails or is not configured.
        """
        try:
            # Try to load LLM client; gracefully skip if not available
            from core.llm_client import LLMClient  # noqa: F811
        except ImportError:
            logger.debug("LLM client not available, skipping LLM tier for next actions")
            return None

        async with async_session_factory() as session:
            # Gather context
            diligence_items = await list_diligence_items(session, deal_id=self.deal_id)
            ledger = await get_latest_confidence_ledger(session, self.deal_id)
            view = await get_latest_investment_view(session, self.deal_id)

            open_diligence = [
                f"- {d.title} ({d.status}, priority: {d.priority})"
                for d in diligence_items
                if d.status != "complete"
            ]
            evidence_gaps = []
            if ledger and ledger.factors:
                evidence_gaps = [
                    f"- {name}: {f.get('status', 'UNKNOWN')}"
                    for name, f in ledger.factors.items()
                    if f.get("status") in ("UNKNOWN", "CONFLICTING")
                ]

            view_text = ""
            if view and view.content:
                view_text = view.content.get("text", "")[:500]

            prompt = f"""You are a senior PE associate with 10+ years of experience. Based on the following deal state, what is the single most important next action?

Deal ID: {self.deal_id}
Stage: {self.stage}
Confidence Score: {ledger.final_score if ledger else 'N/A'}%

Open diligence items:
{chr(10).join(open_diligence) if open_diligence else 'None'}

Evidence gaps / conflicts:
{chr(10).join(evidence_gaps) if evidence_gaps else 'None'}

Current investment view (excerpt):
{view_text or 'No view available'}

Respond ONLY with a JSON object in this exact format:
{{
    "action": "One-sentence specific action",
    "rationale": "One-sentence business rationale",
    "priority": "CRITICAL|HIGH|MEDIUM"
}}

Be concise and specific. No preamble."""

            try:
                client = LLMClient()
                response = await client.complete(prompt, temperature=0.3, max_tokens=200)
                text = response.strip()
                # Extract JSON if wrapped in markdown
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()

                result = json.loads(text)
                return {
                    "id": "llm-suggested",
                    "title": result["action"],
                    "description": result["rationale"],
                    "priority": result["priority"].lower(),
                    "category": "llm",
                    "rationale": result["rationale"],
                }
            except Exception as exc:
                logger.warning("LLM next action generation failed: %s", exc)
                return None


# ── Combined Engine ──────────────────────────────────────────────────────────


class NextActionsEngine:
    """Unified next actions engine: rule-based + LLM, with caching."""

    def __init__(self, deal_id: int, stage: str):
        self.deal_id = deal_id
        self.stage = stage

    async def _capture_state(self) -> dict[str, Any]:
        """Capture a snapshot of the current deal state for cache key generation."""
        async with async_session_factory() as session:
            diligence_items = await list_diligence_items(session, deal_id=self.deal_id)
            ledger = await get_latest_confidence_ledger(session, self.deal_id)
            view = await get_latest_investment_view(session, self.deal_id)

            return {
                "stage": self.stage,
                "diligence_count": len(diligence_items),
                "complete_count": sum(1 for d in diligence_items if d.status == "complete"),
                "blocker_count": sum(1 for d in diligence_items if d.priority == "blocker" and d.status != "complete"),
                "confidence_score": ledger.final_score if ledger else None,
                "view_status": view.status if view else None,
                "view_version": view.version if view else None,
            }

    async def generate(self, use_llm: bool = True) -> list[dict[str, Any]]:
        """Generate next actions. Cached for 30 minutes unless state changes."""
        state = await self._capture_state()
        state_key = _make_state_key(self.deal_id, state)

        cached = _get_cached(self.deal_id, state_key)
        if cached is not None:
            return cached

        # Rule-based tier (always run)
        rule_engine = RuleBasedNextActions(self.deal_id, self.stage)
        actions = await rule_engine.generate()

        # LLM tier (optional, adds one nuanced action if available)
        if use_llm and len(actions) < 3:
            llm_engine = LLMNextActions(self.deal_id, self.stage)
            llm_action = await llm_engine.generate()
            if llm_action:
                actions.insert(0, llm_action)  # LLM action gets top priority

        _set_cached(self.deal_id, state_key, actions)
        return actions

    async def invalidate_cache(self) -> None:
        """Clear the cache for this deal (call after any state mutation)."""
        keys_to_remove = [k for k in _next_action_cache if k.startswith(f"{self.deal_id}:")]
        for k in keys_to_remove:
            del _next_action_cache[k]

    @staticmethod
    def clear_all_cache() -> None:
        """Clear the entire next actions cache."""
        _next_action_cache.clear()
