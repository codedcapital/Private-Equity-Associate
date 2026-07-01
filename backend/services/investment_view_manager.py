"""Investment View Manager — Seeds, edits, and versions the investment narrative.

The Investment View is the center of gravity for the new Overview page.
It is:
1. Seeded by the AI (from DecisionOutput.executive_summary)
2. Edited by the associate
3. Versioned on every save
4. Referenced by the memo generator

Usage:
    manager = InvestmentViewManager(deal_id=7)
    # Seed from AI draft
    view = await manager.seed_from_decision(decision)
    # Edit by associate
    v2 = await manager.edit(view.id, content={...}, edited_by="J. Reyes")
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from db.crud import (
    create_deal_event,
    create_investment_view,
    get_investment_view_by_id,
    get_latest_investment_view,
    list_investment_views,
    update_investment_view,
)
from db.models import InvestmentView, InvestmentViewStatus
from db.session import async_session_factory
from schemas.evidence import DecisionOutput

logger = logging.getLogger(__name__)


# ── Default AI draft template ─────────────────────────────────────────────────

DEFAULT_DRAFT_TEMPLATE = """Based on the available evidence, this business appears attractive because {strengths}.

The principal concerns remain {concerns}.

Confidence: {confidence}%"""


class InvestmentViewManager:
    """Manages the lifecycle of an Investment View for a deal."""

    def __init__(self, deal_id: int):
        self.deal_id = deal_id

    async def seed_from_decision(
        self,
        decision: DecisionOutput,
        force: bool = False,
    ) -> InvestmentView:
        """Create the first AI-generated draft from a DecisionOutput.

        If a view already exists and force=False, returns the existing latest view.
        """
        async with async_session_factory() as session:
            latest = await get_latest_investment_view(session, self.deal_id)
            if latest and not force:
                logger.info(
                    "Investment view already exists for deal_id=%s, skipping seed",
                    self.deal_id,
                )
                return latest

            # Build content from executive summary or template
            content = await self._build_draft_content(decision)
            recommendation = decision.recommendation
            confidence_score = int(decision.confidence_score * 100)

            view = await create_investment_view(
                session,
                deal_id=self.deal_id,
                content=content,
                recommendation=recommendation,
                confidence_score=confidence_score,
                authored_by="system",
                status=InvestmentViewStatus.DRAFT.value,
            )

            # Log event
            await create_deal_event(
                session,
                deal_id=self.deal_id,
                event_type="view_updated",
                actor_type="system",
                description=f"AI-generated initial investment view (v{view.version})",
                event_metadata={
                    "version": view.version,
                    "recommendation": recommendation,
                    "confidence_score": confidence_score,
                },
            )

            return view

    async def seed_from_text(
        self,
        text: str,
        recommendation: str | None = None,
        confidence_score: float | None = None,
        authored_by: str = "system",
    ) -> InvestmentView:
        """Seed a view from plain text (used when DecisionOutput is not available)."""
        async with async_session_factory() as session:
            content = {"text": text, "blocks": [{"type": "paragraph", "text": text}]}
            view = await create_investment_view(
                session,
                deal_id=self.deal_id,
                content=content,
                recommendation=recommendation,
                confidence_score=confidence_score,
                authored_by=authored_by,
                status=InvestmentViewStatus.DRAFT.value,
            )
            return view

    async def edit(
        self,
        view_id: int,
        content: dict | None = None,
        recommendation: str | None = None,
        confidence_score: float | None = None,
        edited_by: str = "unknown",
        status: str | None = None,
    ) -> InvestmentView:
        """Edit an existing view, creating a new version on save."""
        async with async_session_factory() as session:
            old_view = await get_investment_view_by_id(session, view_id)
            if not old_view:
                raise ValueError(f"Investment view {view_id} not found")

            # Create a new version with the edited content
            new_content = content if content is not None else old_view.content
            new_recommendation = recommendation if recommendation is not None else old_view.recommendation
            new_confidence = confidence_score if confidence_score is not None else old_view.confidence_score
            new_status = status if status is not None else old_view.status

            new_view = await create_investment_view(
                session,
                deal_id=self.deal_id,
                content=new_content,
                recommendation=new_recommendation,
                confidence_score=new_confidence,
                authored_by=old_view.authored_by,
                status=new_status,
            )
            # Update edited_by on the new version
            await update_investment_view(session, new_view.id, edited_by=edited_by)
            await session.refresh(new_view)

            # Log event with diff
            diff = {}
            if content is not None and content != old_view.content:
                diff["content_changed"] = True
            if recommendation is not None and recommendation != old_view.recommendation:
                diff["recommendation_changed"] = {"from": old_view.recommendation, "to": recommendation}
            if confidence_score is not None and confidence_score != old_view.confidence_score:
                diff["confidence_changed"] = {"from": old_view.confidence_score, "to": confidence_score}

            await create_deal_event(
                session,
                deal_id=self.deal_id,
                event_type="view_updated",
                actor_type="user",
                actor_id=edited_by,
                description=f"Investment view edited by {edited_by} (v{new_view.version})",
                event_metadata=diff,
            )

            return new_view

    async def get_latest(self) -> InvestmentView | None:
        """Get the latest investment view for this deal."""
        async with async_session_factory() as session:
            return await get_latest_investment_view(session, self.deal_id)

    async def get_history(self) -> list[InvestmentView]:
        """Get all versions of the investment view for this deal."""
        async with async_session_factory() as session:
            return list(await list_investment_views(session, self.deal_id))

    @staticmethod
    async def _build_draft_content(decision: DecisionOutput) -> dict[str, Any]:
        """Build the structured content for an AI draft."""
        # Use executive summary if available
        if decision.executive_summary:
            text = decision.executive_summary
        else:
            strengths = ", ".join(decision.top_strengths[:3]) or "strong fundamentals"
            concerns = ", ".join(decision.top_concerns[:3]) or "valuation"
            text = DEFAULT_DRAFT_TEMPLATE.format(
                strengths=strengths,
                concerns=concerns,
                confidence=int(decision.confidence_score * 100),
            )

        return {
            "text": text,
            "blocks": [
                {"type": "paragraph", "text": text},
            ],
            "sources": decision.data_sources,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def finalize(self, view_id: int, finalized_by: str) -> InvestmentView:
        """Mark a view as FINAL (ready for IC)."""
        async with async_session_factory() as session:
            view = await update_investment_view(
                session, view_id, status=InvestmentViewStatus.FINAL.value
            )
            if view:
                await create_deal_event(
                    session,
                    deal_id=self.deal_id,
                    event_type="view_updated",
                    actor_type="user",
                    actor_id=finalized_by,
                    description=f"Investment view v{view.version} marked as FINAL",
                )
            return view
