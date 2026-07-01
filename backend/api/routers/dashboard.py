"""Dashboard router — summary metrics, attention list, and score refresh.

Endpoints:
    GET    /dashboard/summary          — Pipeline summary statistics
    GET    /dashboard/attention         — Deals requiring attention
    POST   /dashboard/scores/{deal_id}/refresh — Recompute deal score
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from db.crud import (
    dismiss_signal,
    get_signal_by_id,
    list_signals,
)
from db.models import (
    ActivityLog,
    AgentLog,
    Company,
    Deal,
    DealScore,
    ScoreHistory,
    Signal,
)
from db.session import async_session_factory
from schemas.dashboard import (
    AttentionDeal,
    AttentionList,
    DashboardSummary,
    ScoreRefreshResponse,
)
from schemas.signals import SignalList, SignalRead
from services.scoring_engine import ScoringEngine

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/health")
async def health() -> dict:
    """Health check for the dashboard router."""
    return {"status": "ok"}


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary() -> DashboardSummary:
    """Return pipeline summary statistics."""
    async with async_session_factory() as session:
        # Query all deals and their scores
        deals_result = await session.execute(select(Deal))
        deals = deals_result.scalars().all()

        scores_result = await session.execute(
            select(DealScore).where(DealScore.score.isnot(None))
        )
        scores = scores_result.scalars().all()
        score_map = {s.deal_id: s for s in scores}

        # Stage breakdown
        stage_breakdown = {
            "sourcing": 0,
            "diligence": 0,
            "ic_ready": 0,
            "passed": 0,
            "closed": 0,
        }
        for deal in deals:
            stage_breakdown[deal.stage.value] = stage_breakdown.get(
                deal.stage.value, 0
            ) + 1

        active_deals = len(
            [d for d in deals if d.stage.value not in ("passed", "rejected")]
        )

        avg_score = (
            round(sum(s.score for s in scores) / len(scores)) if scores else 0
        )
        ic_ready_count = stage_breakdown.get("ic_ready", 0)

        # Attention count: ic_ready OR score_change > 3 in last 7 days OR confidence LOW
        cutoff = datetime.utcnow() - timedelta(days=7)
        attention_count = 0

        for deal in deals:
            if deal.stage.value == "ic_ready":
                attention_count += 1
                continue

            score = score_map.get(deal.id)
            if score and score.confidence == "LOW":
                attention_count += 1
                continue

            # Check score history in last 7 days for changes > 3
            history_result = await session.execute(
                select(ScoreHistory)
                .where(ScoreHistory.deal_id == deal.id)
                .where(ScoreHistory.created_at >= cutoff)
                .order_by(ScoreHistory.created_at)
            )
            history = history_result.scalars().all()
            if len(history) >= 2:
                first_score = history[0].score
                last_score = history[-1].score
                if abs(last_score - first_score) > 3:
                    attention_count += 1

        return DashboardSummary(
            active_deals=active_deals,
            avg_score=avg_score,
            ic_ready_count=ic_ready_count,
            attention_count=attention_count,
            stage_breakdown=stage_breakdown,
            last_updated=datetime.utcnow().isoformat() + "Z",
        )


@router.get("/attention", response_model=AttentionList)
async def get_attention_deals() -> AttentionList:
    """Return deals requiring attention, sorted by score descending."""
    async with async_session_factory() as session:
        cutoff = datetime.utcnow() - timedelta(days=7)

        # Get all deals with company info
        deals_result = await session.execute(
            select(Deal, Company).join(Company, Deal.company_id == Company.id)
        )
        deal_rows = deals_result.all()

        scores_result = await session.execute(select(DealScore))
        score_map = {s.deal_id: s for s in scores_result.scalars().all()}

        attention_deals: list[AttentionDeal] = []

        for deal, company in deal_rows:
            score_obj = score_map.get(deal.id)
            is_attention = False
            score_change = 0
            score_change_direction = "none"
            why = ""

            if deal.stage.value == "ic_ready":
                is_attention = True
                why = "IC Ready"
            elif score_obj is None:
                is_attention = True
                why = "Not yet scored"
            else:
                # Check score history in last 7 days
                history_result = await session.execute(
                    select(ScoreHistory)
                    .where(ScoreHistory.deal_id == deal.id)
                    .where(ScoreHistory.created_at >= cutoff)
                    .order_by(ScoreHistory.created_at.desc())
                )
                history_entries = history_result.scalars().all()

                if history_entries:
                    latest = history_entries[0]

                    # Get previous entry before the latest one
                    prev_result = await session.execute(
                        select(ScoreHistory)
                        .where(ScoreHistory.deal_id == deal.id)
                        .where(ScoreHistory.created_at < latest.created_at)
                        .order_by(ScoreHistory.created_at.desc())
                        .limit(1)
                    )
                    previous = prev_result.scalar_one_or_none()

                    if previous:
                        score_change = latest.score - previous.score
                    else:
                        score_change = 0

                    if score_change <= -10 or score_change >= 5:
                        is_attention = True
                        score_change_direction = (
                            "up" if score_change > 0 else "down"
                        )
                        why = latest.reason or "Score updated"

            if is_attention:
                attention_deals.append(
                    AttentionDeal(
                        deal_id=deal.id,
                        company_id=company.id,
                        company_name=company.name,
                        ticker=company.ticker,
                        score=score_obj.score if score_obj else None,
                        score_change=score_change,
                        score_change_direction=score_change_direction,
                        stage=deal.stage.value,
                        stage_label=deal.stage.value.replace("_", " ").title(),
                        why=why,
                        confidence=score_obj.confidence if score_obj else "INSUFFICIENT",
                        updated_at=(
                            score_obj.updated_at.isoformat()
                            if score_obj
                            else deal.last_updated.isoformat()
                        ),
                        financials_score=score_obj.financials_score if score_obj else None,
                        risk_score=score_obj.risk_score if score_obj else None,
                        moat_score=score_obj.moat_score if score_obj else None,
                        market_score=score_obj.market_score if score_obj else None,
                    )
                )

        # Sort by score descending (nulls last)
        attention_deals.sort(
            key=lambda d: (d.score is None, -(d.score or 0))
        )

        return AttentionList(deals=attention_deals)


@router.post("/scores/{deal_id}/refresh", response_model=ScoreRefreshResponse)
async def refresh_deal_score(deal_id: int) -> ScoreRefreshResponse:
    """Trigger a score recomputation for a deal and return the new score."""
    from db.crud import get_deal_by_id

    async with async_session_factory() as session:
        deal = await get_deal_by_id(session, deal_id)
        if not deal:
            raise HTTPException(
                status_code=404, detail=f"Deal {deal_id} not found"
            )

    engine = ScoringEngine(deal_id=deal.id, company_id=deal.company_id)
    result = await engine.compute_score()

    return ScoreRefreshResponse(
        deal_id=result["deal_id"],
        score=result["score"],
        financials_score=result["financials_score"],
        moat_score=result["moat_score"],
        market_score=result["market_score"],
        risk_score=result["risk_score"],
        confidence=result["confidence"],
        reason=result["reason"],
    )


@router.get("/signals", response_model=SignalList)
async def get_signals(deal_id: int | None = None) -> SignalList:
    """Return recent signals across all deals (or filtered by deal_id)."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Signal, Company)
            .join(Deal, Signal.deal_id == Deal.id)
            .join(Company, Deal.company_id == Company.id)
            .where(Signal.is_dismissed == False)
            .order_by(Signal.detected_at.desc())
            .limit(50)
        )
        rows = result.all()
        signal_reads = []
        for signal, company in rows:
            signal_reads.append(
                SignalRead(
                    id=signal.id,
                    deal_id=signal.deal_id,
                    company_name=company.name if company else None,
                    signal_type=signal.signal_type,
                    direction=signal.direction,
                    title=signal.title,
                    description=signal.description,
                    evidence_url=signal.evidence_url,
                    evidence_text=signal.evidence_text,
                    confidence=signal.confidence,
                    detected_at=signal.detected_at.isoformat() if signal.detected_at else None,
                    resolved_at=signal.resolved_at.isoformat() if signal.resolved_at else None,
                    is_dismissed=signal.is_dismissed,
                    metadata=signal.event_metadata,
                )
            )
        return SignalList(signals=signal_reads)


@router.post("/signals/{signal_id}/dismiss")
async def dismiss_signal_endpoint(signal_id: int) -> dict:
    """Dismiss a signal."""
    async with async_session_factory() as session:
        signal = await get_signal_by_id(session, signal_id)
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        await dismiss_signal(session, signal_id)
        return {"success": True, "signal_id": signal_id}


@router.get("/recently-updated")
async def get_recently_updated() -> dict:
    """Return recent activity from the last 24 hours."""
    async with async_session_factory() as session:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        result = await session.execute(
            select(ActivityLog, Deal, Company)
            .join(Deal, ActivityLog.deal_id == Deal.id)
            .join(Company, Deal.company_id == Company.id)
            .where(ActivityLog.created_at >= cutoff)
            .order_by(ActivityLog.created_at.desc())
            .limit(20)
        )
        rows = result.all()
        items = []
        for log, deal, company in rows:
            items.append(
                {
                    "deal_id": deal.id,
                    "company_name": company.name if company else f"Deal {deal.id}",
                    "event_type": log.event_type,
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                    "reason": log.reason,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
            )
        return {"items": items}


@router.get("/activity-summary")
async def get_activity_summary() -> dict:
    """Return daily activity counts from agent logs."""
    async with async_session_factory() as session:
        from datetime import date

        today = date.today()
        result = await session.execute(
            select(AgentLog.agent_name, func.count(AgentLog.id))
            .where(func.cast(AgentLog.created_at, func.Date) == today)
            .group_by(AgentLog.agent_name)
        )
        counts = dict(result.all())
        return {
            "financials_refreshed": counts.get("financials", 0),
            "research_updated": counts.get("research", 0),
            "news_analyzed": counts.get("news", 0),
            "models_rebuilt": counts.get("lbo", 0),
            "total_runs": sum(counts.values()),
            "date": today.isoformat(),
        }


@router.get("/industry")
async def get_industry_watch() -> dict:
    """Return sector breakdown from pipeline companies with median metrics."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Company.sector, func.count(Deal.id))
            .join(Deal, Company.id == Deal.company_id)
            .where(Company.sector.isnot(None))
            .group_by(Company.sector)
        )
        sectors = []
        for sector, count in result.all():
            sectors.append({"sector": sector, "count": count})
        return {"sectors": sectors}


@router.get("/search")
async def global_search(q: str = "") -> dict:
    """Simple global search across companies and deals."""
    if not q or len(q) < 2:
        return {"results": []}
    async with async_session_factory() as session:
        q_lower = f"%{q.lower()}%"
        # Search companies
        company_result = await session.execute(
            select(Company).where(func.lower(Company.name).like(q_lower)).limit(10)
        )
        companies = company_result.scalars().all()
        # Search deals by company
        deal_result = await session.execute(
            select(Deal, Company)
            .join(Company, Deal.company_id == Company.id)
            .where(func.lower(Company.name).like(q_lower))
            .limit(10)
        )
        deals = deal_result.all()
        results = []
        for c in companies:
            results.append(
                {
                    "type": "company",
                    "id": c.id,
                    "title": c.name,
                    "subtitle": c.ticker or c.sector or "",
                    "url": f"/deal/{c.id}",
                }
            )
        for deal, company in deals:
            results.append(
                {
                    "type": "deal",
                    "id": deal.id,
                    "title": company.name,
                    "subtitle": f"Stage: {deal.stage.value}",
                    "url": f"/deal/{deal.id}",
                }
            )
        return {"results": results}
