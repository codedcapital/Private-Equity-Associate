"""Overview router — Single-page Investment Decision Pack.

Endpoints:
    GET    /deals/{deal_id}/overview              — Full overview page data
    POST   /deals/{deal_id}/overview/investment-view — Create or edit investment view
    GET    /deals/{deal_id}/overview/investment-view/history — All versions
    POST   /deals/{deal_id}/overview/diligence   — Add diligence item
    PATCH  /deals/{deal_id}/overview/diligence/{item_id} — Update diligence item
    DELETE /deals/{deal_id}/overview/diligence/{item_id} — Remove diligence item
    GET    /deals/{deal_id}/overview/confidence  — Confidence ledger breakdown
    GET    /deals/{deal_id}/overview/readiness   — Decision readiness score
    GET    /deals/{deal_id}/overview/events      — Recent activity feed
    POST   /deals/{deal_id}/overview/refresh     — Refresh from intelligence engine
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.auth import UserContext, UserRole, get_current_user, require_role
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from db.crud import (
    create_deal_event,
    create_diligence_item,
    delete_diligence_item,
    get_confidence_ledger_by_id,
    get_deal_by_id,
    get_diligence_item_by_id,
    get_evidence_item_by_id,
    get_hub_by_company,
    get_investment_view_by_id,
    get_latest_confidence_ledger,
    get_latest_investment_view,
    list_confidence_ledgers,
    list_deal_events,
    list_diligence_items,
    list_evidence_items,
    list_investment_views,
    update_diligence_item,
    update_evidence_item,
    update_investment_view,
)
from db.models import (
    Deal,
    DealEvent,
    DiligenceItem,
    EvidenceItem,
    EvidenceStatus,
    InvestmentView,
)
from db.session import async_session_factory
from services.change_summarizer import ChangeSummarizer
from services.next_actions_engine import NextActionsEngine
from schemas.overview import (
    EvidenceStatusUpdate,
    EvidenceConflictCreate,
    InvestmentViewDiffQuery,
    DealSettingsUpdate,
    DealSettingsRead,
)
from schemas.diligence import DiligenceItemCreate, DiligenceItemRead, DiligenceItemUpdate
from schemas.investment_view import InvestmentViewCreate, InvestmentViewRead, InvestmentViewUpdate
from services.confidence_ledger_builder import ConfidenceLedgerBuilder
from services.decision_readiness import DecisionReadiness
from services.evidence_status_mapper import EvidenceStatusMapper
from services.investment_view_manager import InvestmentViewManager
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/deals", tags=["overview"])
logger = logging.getLogger(__name__)


# ── Helper: build full overview response ─────────────────────────────────────


async def _build_overview(deal_id: int) -> dict[str, Any]:
    """Assemble the full overview page data for a deal."""
    async with async_session_factory() as session:
        from sqlalchemy import select
        from db.models import Company

        # 1. Deal + Company (eagerly loaded)
        deal_result = await session.execute(
            select(Deal)
            .options(selectinload(Deal.company))
            .where(Deal.id == deal_id)
        )
        deal = deal_result.scalar_one_or_none()
        if not deal:
            raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

        company = deal.company
        if not company:
            raise HTTPException(status_code=404, detail=f"Company for deal {deal_id} not found")

        # 2. Investment View (latest)
        view = await get_latest_investment_view(session, deal_id)
        view_data = None
        if view:
            view_data = InvestmentViewRead.model_validate(view).model_dump()

        # 3. Confidence Ledger (latest)
        ledger = await get_latest_confidence_ledger(session, deal_id)
        confidence_data = None
        if ledger:
            confidence_data = ConfidenceLedgerBuilder.to_breakdown(ledger)

        # 4. Evidence from Intelligence Hub
        hub = await get_hub_by_company(session, company.id)
        evidence_list: list[dict] = []
        if hub:
            items = await list_evidence_items(session, hub_id=hub.id)
            mapper = EvidenceStatusMapper()
            for item in items:
                status = item.evidence_status or mapper.classify_evidence_item(item)
                evidence_list.append(
                    {
                        "id": item.id,
                        "module_name": item.source,
                        "text": item.text,
                        "status": status.value if isinstance(status, EvidenceStatus) else status,
                        "source": item.source,
                        "source_type": item.source_type,
                        "confidence": item.confidence,
                        "is_supporting": item.is_supporting,
                        "is_contradictory": item.is_contradictory,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                    }
                )

        # 5. Diligence Items
        diligence_items = await list_diligence_items(session, deal_id=deal_id)
        diligence_data = [DiligenceItemRead.model_validate(d).model_dump() for d in diligence_items]

        # 6. Decision Readiness
        readiness = await DecisionReadiness(deal_id, deal.stage.value).compute()

        # 7. Recent Events (last 10)
        events = await list_deal_events(session, deal_id=deal_id, limit=10)
        events_data = [
            {
                "id": e.id,
                "event_type": e.event_type,
                "actor_type": e.actor_type,
                "actor_id": e.actor_id,
                "description": e.description,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]

        # 8. Financial snapshot (latest)
        from db.models import Financial
        fin_result = await session.execute(
            select(Financial)
            .where(Financial.company_id == company.id)
            .order_by(Financial.report_date.desc())
            .limit(1)
        )
        fin = fin_result.scalar_one_or_none()
        financial_snapshot = None
        if fin:
            financial_snapshot = {
                "revenue": fin.revenue,
                "ebitda": fin.ebitda,
                "ebitda_margin": fin.ebitda_margin,
                "revenue_growth": fin.revenue_growth,
                "net_debt": fin.net_debt,
                "net_debt_ebitda": fin.net_debt_ebitda,
                "fcf": fin.fcf,
                "fcf_yield": fin.fcf_yield,
            }

        return {
            "deal_id": deal_id,
            "company": {
                "id": company.id,
                "name": company.name,
                "ticker": company.ticker,
                "sector": company.sector,
                "geography": company.geography,
            },
            "stage": deal.stage.value,
            "investment_view": view_data,
            "confidence": confidence_data,
            "evidence": evidence_list,
            "diligence": {
                "items": diligence_data,
                "total": len(diligence_data),
                "complete": sum(1 for d in diligence_data if d["status"] == "complete"),
                "open": sum(1 for d in diligence_data if d["status"] != "complete"),
            },
            "decision_readiness": readiness,
            "recent_events": events_data,
            "financial_snapshot": financial_snapshot,
            "lbo": {
                "entry_ev": deal.entry_ev,
                "entry_ebitda": deal.entry_ebitda,
                "lbo_irr": deal.lbo_irr,
                "lbo_moic": deal.lbo_moic,
            },
        }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/{deal_id}/overview")
async def get_overview(deal_id: int) -> dict[str, Any]:
    """Get the full overview page data for a deal."""
    return await _build_overview(deal_id)


# ── Investment View ────────────────────────────────────────────────────────────


@router.post("/{deal_id}/overview/investment-view")
async def create_or_edit_investment_view(
    deal_id: int, payload: InvestmentViewCreate
) -> dict[str, Any]:
    """Create a new investment view or edit an existing one (creates a new version)."""
    async with async_session_factory() as session:
        deal = await get_deal_by_id(session, deal_id)
        if not deal:
            raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

        latest = await get_latest_investment_view(session, deal_id)
        manager = InvestmentViewManager(deal_id=deal_id)

        if latest and payload.content:
            # Editing existing view
            edited = await manager.edit(
                latest.id,
                content=payload.content,
                recommendation=payload.recommendation,
                confidence_score=payload.confidence_score,
                edited_by=payload.authored_by,
            )
            return InvestmentViewRead.model_validate(edited).model_dump()
        else:
            # Creating new view
            view = await create_investment_view(
                session,
                deal_id=deal_id,
                content=payload.content,
                recommendation=payload.recommendation,
                confidence_score=payload.confidence_score,
                authored_by=payload.authored_by,
                status=payload.status,
            )
            return InvestmentViewRead.model_validate(view).model_dump()


@router.get("/{deal_id}/overview/investment-view/history")
async def get_investment_view_history(deal_id: int) -> dict[str, Any]:
    """Get all versions of the investment view for a deal."""
    async with async_session_factory() as session:
        views = await list_investment_views(session, deal_id)
        return {
            "deal_id": deal_id,
            "views": [InvestmentViewRead.model_validate(v).model_dump() for v in views],
            "total_versions": len(views),
        }


# ── Diligence ───────────────────────────────────────────────────────────────


@router.post("/{deal_id}/overview/diligence")
async def add_diligence_item(deal_id: int, payload: DiligenceItemCreate) -> dict[str, Any]:
    """Add a new diligence item to a deal."""
    async with async_session_factory() as session:
        deal = await get_deal_by_id(session, deal_id)
        if not deal:
            raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

        item = await create_diligence_item(
            session,
            deal_id=deal_id,
            category=payload.category,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            assigned_to=payload.assigned_to,
            due_date=payload.due_date,
            evidence_id=payload.evidence_id,
            priority=payload.priority,
            created_by=payload.created_by,
        )

        await create_deal_event(
            session,
            deal_id=deal_id,
            event_type="diligence_status_changed",
            actor_type="user",
            actor_id=payload.created_by,
            description=f"Diligence item created: {payload.title}",
            event_metadata={"item_id": item.id, "status": payload.status},
        )

        return DiligenceItemRead.model_validate(item).model_dump()


@router.patch("/{deal_id}/overview/diligence/{item_id}")
async def update_diligence_item_endpoint(
    deal_id: int, item_id: int, payload: DiligenceItemUpdate
) -> dict[str, Any]:
    """Update a diligence item."""
    async with async_session_factory() as session:
        item = await get_diligence_item_by_id(session, item_id)
        if not item or item.deal_id != deal_id:
            raise HTTPException(status_code=404, detail="Diligence item not found")

        update_data = payload.model_dump(exclude_unset=True)
        old_status = item.status

        updated = await update_diligence_item(session, item_id, **update_data)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update diligence item")

        # Log status change if applicable
        if "status" in update_data and update_data["status"] != old_status:
            await create_deal_event(
                session,
                deal_id=deal_id,
                event_type="diligence_status_changed",
                actor_type="user",
                description=f"Diligence '{item.title}' status changed from {old_status} to {update_data['status']}",
                event_metadata={"item_id": item_id, "from": old_status, "to": update_data["status"]},
            )

        return DiligenceItemRead.model_validate(updated).model_dump()


@router.delete("/{deal_id}/overview/diligence/{item_id}")
async def delete_diligence_item_endpoint(deal_id: int, item_id: int) -> dict[str, Any]:
    """Delete a diligence item."""
    async with async_session_factory() as session:
        item = await get_diligence_item_by_id(session, item_id)
        if not item or item.deal_id != deal_id:
            raise HTTPException(status_code=404, detail="Diligence item not found")

        success = await delete_diligence_item(session, item_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete diligence item")

        return {"deleted": True, "item_id": item_id}


# ── Confidence ─────────────────────────────────────────────────────────────────


@router.get("/{deal_id}/overview/confidence")
async def get_confidence_breakdown(deal_id: int) -> dict[str, Any]:
    """Get the confidence ledger breakdown for a deal."""
    async with async_session_factory() as session:
        ledger = await get_latest_confidence_ledger(session, deal_id)
        if not ledger:
            raise HTTPException(
                status_code=404,
                detail="No confidence ledger found. Run the pipeline first.",
            )
        return ConfidenceLedgerBuilder.to_breakdown(ledger)


# ── Decision Readiness ─────────────────────────────────────────────────────────


@router.get("/{deal_id}/overview/readiness")
async def get_decision_readiness(deal_id: int) -> dict[str, Any]:
    """Get the decision readiness score and checklist for a deal."""
    async with async_session_factory() as session:
        deal = await get_deal_by_id(session, deal_id)
        if not deal:
            raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

        readiness = DecisionReadiness(deal_id, deal.stage.value)
        return await readiness.compute()


# ── Events ─────────────────────────────────────────────────────────────────────


@router.get("/{deal_id}/overview/events")
async def get_recent_events(deal_id: int, limit: int = 20) -> dict[str, Any]:
    """Get recent activity events for a deal."""
    async with async_session_factory() as session:
        events = await list_deal_events(session, deal_id=deal_id, limit=limit)
        return {
            "deal_id": deal_id,
            "events": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "actor_type": e.actor_type,
                    "actor_id": e.actor_id,
                    "description": e.description,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ],
            "total": len(events),
        }


# ── Refresh ────────────────────────────────────────────────────────────────────


@router.post("/{deal_id}/overview/refresh")
async def refresh_overview(deal_id: int) -> dict[str, Any]:
    """Refresh overview data from the intelligence engine.

    Re-runs the confidence ledger builder and decision readiness,
    updates the investment view if AI draft is newer.
    If no intelligence hub data exists, returns the current overview
    with whatever data is available (graceful degradation).
    """
    async with async_session_factory() as session:
        deal = await get_deal_by_id(session, deal_id)
        if not deal:
            raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

        hub = await get_hub_by_company(session, deal.company_id)

        if hub and hub.decision_output:
            # Rebuild confidence ledger from cached decision output
            from schemas.evidence import DecisionOutput
            try:
                decision = DecisionOutput.model_validate(hub.decision_output)
            except Exception as exc:
                logger.warning("Cached decision output is corrupted for deal %s: %s", deal_id, exc)
            else:
                builder = ConfidenceLedgerBuilder(deal_id=deal_id)
                await builder.build_from_decision(decision)

                # Seed or update investment view
                manager = InvestmentViewManager(deal_id=deal_id)
                await manager.seed_from_decision(decision, force=False)

                await create_deal_event(
                    session,
                    deal_id=deal_id,
                    event_type="evidence_refreshed",
                    actor_type="system",
                    description="Overview refreshed from intelligence engine",
                    event_metadata={"confidence_score": decision.confidence_score},
                )
        else:
            # No hub data — log but don't fail. Just return current overview.
            logger.info(
                "No intelligence hub data for deal %s. Returning current overview.", deal_id
            )
            await create_deal_event(
                session,
                deal_id=deal_id,
                event_type="evidence_refreshed",
                actor_type="system",
                description="Overview refresh requested — no intelligence hub data available",
                event_metadata={"hub_exists": bool(hub)},
            )

    return await _build_overview(deal_id)


# ── Next Actions ─────────────────────────────────────────────────────────────


@router.get("/{deal_id}/overview/next-actions")
async def get_next_actions(deal_id: int, use_llm: bool = True) -> dict[str, Any]:
    """Get contextual next actions for a deal. Cached for 30 minutes."""
    async with async_session_factory() as session:
        deal = await get_deal_by_id(session, deal_id)
        if not deal:
            raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

        engine = NextActionsEngine(deal_id=deal_id, stage=deal.stage.value)
        actions = await engine.generate(use_llm=use_llm)
        return {"deal_id": deal_id, "actions": actions, "generated_at": datetime.now(timezone.utc).isoformat()}


# ── Evidence ─────────────────────────────────────────────────────────────────


@router.patch("/{deal_id}/overview/evidence/{evidence_id}")
async def update_evidence_status(
    deal_id: int, evidence_id: int, payload: EvidenceStatusUpdate
) -> dict[str, Any]:
    """Update evidence status and trigger confidence recalculation."""
    async with async_session_factory() as session:
        item = await get_evidence_item_by_id(session, evidence_id)
        if not item:
            raise HTTPException(status_code=404, detail="Evidence item not found")

        old_status = item.evidence_status
        new_status = payload.status

        # Update the evidence item
        updated = await update_evidence_item(
            session, evidence_id, evidence_status=new_status
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update evidence status")

        # Log event
        await create_deal_event(
            session,
            deal_id=deal_id,
            event_type="evidence_status_changed",
            actor_type="user",
            description=f"Evidence status changed from {old_status} to {new_status}",
            event_metadata={
                "evidence_id": evidence_id,
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        # If CONFLICTING, create a conflict record if description provided
        if new_status == "conflicting" and payload.conflict_description:
            from db.crud import create_evidence_conflict
            await create_evidence_conflict(
                session,
                evidence_a_id=evidence_id,
                evidence_b_id=evidence_id,
                conflict_description=payload.conflict_description,
                resolution_status="open",
            )

        # Trigger confidence recalculation
        deal = await get_deal_by_id(session, deal_id)
        hub = await get_hub_by_company(session, deal.company_id) if deal else None
        if hub and hub.decision_output:
            from schemas.evidence import DecisionOutput
            try:
                decision = DecisionOutput.model_validate(hub.decision_output)
                builder = ConfidenceLedgerBuilder(deal_id=deal_id)
                ledger = await builder.build_from_decision(decision)

                await create_deal_event(
                    session,
                    deal_id=deal_id,
                    event_type="confidence_recalculated",
                    actor_type="system",
                    description=f"Confidence recalculated after evidence status change",
                    event_metadata={
                        "old_score": ledger.base_score if ledger else None,
                        "new_score": ledger.final_score if ledger else None,
                    },
                )
            except Exception as exc:
                logger.warning("Confidence recalculation failed after evidence update: %s", exc)

        # Invalidate next-actions cache
        engine = NextActionsEngine(deal_id=deal_id, stage=deal.stage.value if deal else "unknown")
        await engine.invalidate_cache()

        return {"updated": True, "evidence_id": evidence_id, "new_status": new_status}


@router.post("/{deal_id}/overview/evidence/{evidence_id}/conflict")
async def create_evidence_conflict_endpoint(
    deal_id: int, evidence_id: int, payload: EvidenceConflictCreate
) -> dict[str, Any]:
    """Create a conflict record between two evidence items."""
    async with async_session_factory() as session:
        item_a = await get_evidence_item_by_id(session, evidence_id)
        item_b = await get_evidence_item_by_id(session, payload.evidence_b_id)
        if not item_a or not item_b:
            raise HTTPException(status_code=404, detail="One or both evidence items not found")

        from db.crud import create_evidence_conflict
        conflict = await create_evidence_conflict(
            session,
            evidence_a_id=evidence_id,
            evidence_b_id=payload.evidence_b_id,
            conflict_description=payload.conflict_description,
            resolution_status="open",
        )

        # Also mark evidence_a as CONFLICTING
        await update_evidence_item(session, evidence_id, evidence_status="conflicting")

        await create_deal_event(
            session,
            deal_id=deal_id,
            event_type="evidence_status_changed",
            actor_type="user",
            description=f"Evidence conflict created: {payload.conflict_description}",
            event_metadata={
                "evidence_a_id": evidence_id,
                "evidence_b_id": payload.evidence_b_id,
                "conflict_id": conflict.id,
            },
        )

        return {"created": True, "conflict_id": conflict.id}


# ── Investment View Diff & Restore ───────────────────────────────────────────


@router.get("/{deal_id}/overview/investment-view/diff")
async def get_investment_view_diff(
    deal_id: int, from_version_id: int, to_version_id: int
) -> dict[str, Any]:
    """Get a diff between two versions of the investment view."""
    summarizer = ChangeSummarizer(deal_id=deal_id)
    try:
        diff = await summarizer.diff_investment_views(from_version_id, to_version_id)
        return {"deal_id": deal_id, **diff}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{deal_id}/overview/investment-view/{version_id}/restore")
async def restore_investment_view_version(deal_id: int, version_id: int) -> dict[str, Any]:
    """Restore a previous version of the investment view (creates a new version)."""
    async with async_session_factory() as session:
        view = await get_investment_view_by_id(session, version_id)
        if not view or view.deal_id != deal_id:
            raise HTTPException(status_code=404, detail="Investment view version not found")

        manager = InvestmentViewManager(deal_id=deal_id)
        restored = await manager.edit(
            view_id=view.id,  # This will create a new version based on this old one
            content=view.content,
            recommendation=view.recommendation,
            confidence_score=view.confidence_score,
            edited_by="system_restore",
        )

        await create_deal_event(
            session,
            deal_id=deal_id,
            event_type="view_updated",
            actor_type="system",
            description=f"Investment view restored from version {view.version} as v{restored.version}",
            event_metadata={"restored_from_version": view.version, "new_version": restored.version},
        )

        return InvestmentViewRead.model_validate(restored).model_dump()


# ── Recent Changes ─────────────────────────────────────────────────────────────


@router.get("/{deal_id}/overview/recent-changes")
async def get_recent_changes(
    deal_id: int, limit: int = 20, time_window_hours: int = 168
) -> dict[str, Any]:
    """Get enhanced, human-readable recent changes for a deal."""
    summarizer = ChangeSummarizer(deal_id=deal_id)
    changes = await summarizer.summarize_recent(limit=limit, time_window_hours=time_window_hours)
    return {"deal_id": deal_id, "changes": changes, "total": len(changes)}


# ── Deal Settings ────────────────────────────────────────────────────────────


@router.get("/{deal_id}/overview/settings")
async def get_deal_settings_endpoint(deal_id: int) -> dict[str, Any]:
    """Get deal settings (confidence weights, etc.)."""
    async with async_session_factory() as session:
        from db.crud import get_deal_settings
        settings = await get_deal_settings(session, deal_id)
        if not settings:
            return {"deal_id": deal_id, "confidence_weights": {}, "updated_at": None}
        return {
            "deal_id": deal_id,
            "confidence_weights": settings.confidence_weights,
            "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
        }


@router.patch("/{deal_id}/overview/settings")
async def update_deal_settings_endpoint(deal_id: int, payload: DealSettingsUpdate) -> dict[str, Any]:
    """Update deal settings (confidence weights). Triggers recalculation."""
    async with async_session_factory() as session:
        from db.crud import upsert_deal_settings
        settings = await upsert_deal_settings(session, deal_id, confidence_weights=payload.confidence_weights)

        # Trigger confidence recalculation with new weights
        deal = await get_deal_by_id(session, deal_id)
        hub = await get_hub_by_company(session, deal.company_id) if deal else None
        if hub and hub.decision_output and payload.confidence_weights:
            from schemas.evidence import DecisionOutput
            try:
                decision = DecisionOutput.model_validate(hub.decision_output)
                builder = ConfidenceLedgerBuilder(deal_id=deal_id)
                # TODO: apply weight overrides to FACTOR_WEIGHTS in builder
                ledger = await builder.build_from_decision(decision)

                await create_deal_event(
                    session,
                    deal_id=deal_id,
                    event_type="confidence_recalculated",
                    actor_type="user",
                    description="Confidence recalculated with updated weight settings",
                    event_metadata={
                        "new_score": ledger.final_score if ledger else None,
                        "weight_override": payload.confidence_weights,
                    },
                )
            except Exception as exc:
                logger.warning("Confidence recalculation after settings update failed: %s", exc)

        return {
            "deal_id": deal_id,
            "confidence_weights": settings.confidence_weights,
            "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
        }


# ── Polling / Status ─────────────────────────────────────────────────────────


@router.get("/{deal_id}/overview/status")
async def get_overview_status(deal_id: int) -> dict[str, Any]:
    """Lightweight polling endpoint — returns last-updated timestamps for each section.

    Frontend polls this every 5–10 seconds. If timestamps change, it refreshes the
    corresponding section.
    """
    async with async_session_factory() as session:
        deal = await get_deal_by_id(session, deal_id)
        if not deal:
            raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

        # Latest investment view
        view = await get_latest_investment_view(session, deal_id)
        view_updated = view.updated_at.isoformat() if view and view.updated_at else None

        # Latest confidence ledger
        ledger = await get_latest_confidence_ledger(session, deal_id)
        confidence_updated = ledger.created_at.isoformat() if ledger and ledger.created_at else None

        # Latest diligence activity
        diligence_items = await list_diligence_items(session, deal_id=deal_id)
        diligence_updated = None
        if diligence_items:
            latest_d = max(diligence_items, key=lambda d: d.created_at or __import__("datetime").datetime.min)
            diligence_updated = latest_d.created_at.isoformat() if latest_d.created_at else None

        # Latest evidence activity
        hub = await get_hub_by_company(session, deal.company_id) if deal else None
        evidence_updated = None
        if hub:
            items = await list_evidence_items(session, hub_id=hub.id)
            if items:
                latest_e = max(items, key=lambda e: e.created_at or __import__("datetime").datetime.min)
                evidence_updated = latest_e.created_at.isoformat() if latest_e.created_at else None

        # Latest event
        events = await list_deal_events(session, deal_id=deal_id, limit=1)
        latest_event = events[0] if events else None
        event_updated = latest_event.created_at.isoformat() if latest_event and latest_event.created_at else None

        # Running modules (check deal_events for evidence_refreshed in last 2 min)
        running_modules = []
        if events:
            cutoff = __import__("datetime").datetime.now(__import__("datetime").timezone.utc) - __import__("datetime").timedelta(minutes=2)
            for e in events[:5]:
                if e.created_at and e.created_at > cutoff and e.event_type in ("evidence_refreshed", "confidence_recalculated"):
                    running_modules.append(e.event_type)

        return {
            "deal_id": deal_id,
            "sections": {
                "investment_view": {"last_updated": view_updated},
                "confidence": {"last_updated": confidence_updated},
                "diligence": {"last_updated": diligence_updated, "count": len(diligence_items)},
                "evidence": {"last_updated": evidence_updated, "count": len(items) if hub else 0},
                "events": {"last_updated": event_updated},
            },
            "running_modules": running_modules,
            "poll_again_in_seconds": 10,
        }
