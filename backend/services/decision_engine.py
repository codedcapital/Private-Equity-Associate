"""Decision Engine — Synthesizes EvidenceModules into an Investment Score.

Takes all intelligence modules for a company, scores each metric,
computes weighted module scores, applies risk penalties, and produces
a DecisionOutput with recommendation.

Rules:
  - Score >= 80 + Confidence >= 0.80 → PROCEED (Strong)
  - Score >= 65 + Confidence >= 0.70 → CONDITIONAL (Moderate)
  - Score < 65 or Confidence < 0.60 → PASS (Weak)
  - Contradictory metrics > 30% of total → Downgrade one level
  - Critical gaps exist → Downgrade one level
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from schemas.evidence import DecisionOutput, EvidenceMetric, EvidenceModule, ModuleScore
from core.llm import LLMClient

logger = logging.getLogger(__name__)


# ── Module weights ──────────────────────────────────────────────────────────

MODULE_WEIGHTS: dict[str, float] = {
    "financial": 0.25,
    "research": 0.20,
    "competitive": 0.20,
    "market": 0.15,
    "valuation": 0.20,
}

MODULE_TO_SUBSCORE: dict[str, str] = {
    "financial": "financial_score",
    "research": "thesis_score",
    "competitive": "competitive_score",
    "market": "market_score",
    "valuation": "valuation_score",
}


# ── Scoring helpers ───────────────────────────────────────────────────────────


def _score_module(module: EvidenceModule) -> int:
    """Score a single module 0-100.

    Based on:
      - Overall confidence (0-1 → 0-100)
      - Supporting vs contradictory metric ratio
      - Number of warnings
    """
    base = int(module.overall_confidence * 100)
    total = len(module.metrics)
    if total == 0:
        return base

    contradictory = sum(1 for m in module.metrics if m.is_contradictory)
    ratio = contradictory / total
    # Penalty for contradictory evidence: up to -20 points
    penalty = int(ratio * 20)
    # Penalty for warnings: -3 per warning, max -15
    warning_penalty = min(len(module.warnings) * 3, 15)

    return max(0, base - penalty - warning_penalty)


def _compute_confidence_score(modules: list[EvidenceModule]) -> float:
    """Weighted confidence across all evidence.

    Each metric's confidence is weighted by source quality and module weight.
    """
    total_weighted_confidence = 0.0
    total_weight = 0.0

    for module in modules:
        weight = MODULE_WEIGHTS.get(module.module_type, 0.15)
        module_confidence = module.overall_confidence
        total_weighted_confidence += module_confidence * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0
    return total_weighted_confidence / total_weight


def _compute_risk_score(modules: list[EvidenceModule]) -> int:
    """Compute risk score 0-100. Lower = safer."""
    # Collect all contradictory metrics
    contradictory = []
    for module in modules:
        for metric in module.metrics:
            if metric.is_contradictory:
                contradictory.append(metric)

    if not contradictory:
        return 20  # Base risk for any investment

    # Weight by confidence of contradictory evidence
    # High-confidence contradictory evidence = higher risk
    weighted_risk = sum(m.confidence * 100 for m in contradictory) / len(contradictory)
    # Scale: 0-100 contradictory evidence → 20-80 risk range
    return min(100, 20 + int(weighted_risk * 0.6))


def _recommendation(score: int, confidence: float, risk_score: int, critical_gaps: list[str]) -> tuple[str, str]:
    """Determine recommendation and conviction level."""
    has_critical_gaps = len(critical_gaps) > 0
    risk_penalty = risk_score > 60  # High risk

    # Base recommendation
    if score >= 80 and confidence >= 0.80:
        rec = "PROCEED"
        conv = "STRONG"
    elif score >= 65 and confidence >= 0.70:
        rec = "CONDITIONAL"
        conv = "MODERATE"
    elif score >= 50 and confidence >= 0.60:
        rec = "CONDITIONAL"
        conv = "WEAK"
    else:
        rec = "PASS"
        conv = "WEAK"

    # Downgrade logic
    if has_critical_gaps or risk_penalty:
        if rec == "PROCEED":
            rec = "CONDITIONAL"
            conv = "MODERATE"
        elif rec == "CONDITIONAL":
            rec = "PASS"
            conv = "WEAK"

    return rec, conv


# ── LLM synthesis ─────────────────────────────────────────────────────────────


async def _synthesize_executive_summary(
    modules: list[EvidenceModule],
    investment_score: int,
    recommendation: str,
) -> str | None:
    """Use LLM to produce a one-paragraph investment recommendation with citations."""
    llm = LLMClient()
    try:
        # Build context from all evidence
        parts = []
        for module in modules:
            parts.append(f"\n=== {module.module_type.upper()} ===")
            for m in module.metrics[:5]:  # Top 5 per module
                tag = "✓" if m.is_supporting else "✗" if m.is_contradictory else "-"
                parts.append(f"{tag} {m.name}: {m.value} (confidence: {m.confidence:.0%}) — {m.evidence_text[:120]}")
            for insight in module.key_insights[:3]:
                parts.append(f"Insight: {insight}")
            for warning in module.warnings[:2]:
                parts.append(f"Warning: {warning}")

        context = "\n".join(parts)

        system_prompt = (
            "You are a senior PE partner writing a one-paragraph investment recommendation. "
            "Be concise, specific, and cite the evidence directly. Do not use generic language. "
            "Format: 'We recommend [PROCEED/CONDITIONAL/PASS] because [3-4 specific evidence points]. "
            "Key risks are [specific risks].'"
        )
        user_prompt = (
            f"Investment Score: {investment_score}/100\n"
            f"Recommendation: {recommendation}\n\n"
            f"Evidence:\n{context}\n\n"
            "Write exactly one paragraph (3-5 sentences)."
        )

        return await llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )
    except Exception as exc:
        logger.warning("LLM synthesis failed: %s", exc)
        return None


# ── Decision Engine ──────────────────────────────────────────────────────────


class DecisionEngine:
    """Synthesizes EvidenceModules into an Investment Decision."""

    def __init__(self, company_id: int):
        self.company_id = company_id

    async def decide(
        self,
        modules: list[EvidenceModule],
        include_llm_synthesis: bool = True,
    ) -> DecisionOutput:
        """Compute the final investment decision from all evidence modules."""
        # 1. Score each module
        module_scores: list[ModuleScore] = []
        sub_scores: dict[str, int] = {}

        for module in modules:
            score = _score_module(module)
            supporting = sum(1 for m in module.metrics if m.is_supporting)
            contradictory = sum(1 for m in module.metrics if m.is_contradictory)
            warnings = len(module.warnings)

            ms = ModuleScore(
                module_type=module.module_type,
                score=score,
                confidence=module.overall_confidence,
                supporting_count=supporting,
                contradictory_count=contradictory,
                warning_count=warnings,
            )
            module_scores.append(ms)

            subscore_key = MODULE_TO_SUBSCORE.get(module.module_type)
            if subscore_key:
                sub_scores[subscore_key] = score

        # 2. Weighted investment score
        weighted_score = 0.0
        for ms in module_scores:
            weight = MODULE_WEIGHTS.get(ms.module_type, 0.15)
            weighted_score += ms.score * weight
        investment_score = int(weighted_score)

        # 3. Confidence score
        confidence_score = _compute_confidence_score(modules)

        # 4. Risk score
        risk_score = _compute_risk_score(modules)

        # 5. Evidence counts
        total_metrics = sum(len(m.metrics) for m in modules)
        supporting = sum(ms.supporting_count for ms in module_scores)
        contradictory = sum(ms.contradictory_count for ms in module_scores)
        # Open questions from remaining_diligence category
        open_questions = 0
        # (Will be populated from hub later)

        # 6. Critical gaps (contradictory evidence with high confidence)
        critical_gaps = []
        for module in modules:
            for metric in module.metrics:
                if metric.is_contradictory and metric.confidence >= 0.75:
                    critical_gaps.append(f"{metric.name}: {metric.evidence_text[:100]}")
        critical_gaps = critical_gaps[:5]

        # 7. Top strengths and concerns
        top_strengths = []
        top_concerns = []
        for module in modules:
            for metric in module.metrics:
                if metric.is_supporting and metric.confidence >= 0.75 and len(top_strengths) < 5:
                    top_strengths.append(f"{metric.name}: {metric.value} — {metric.evidence_text[:80]}")
                if metric.is_contradictory and metric.confidence >= 0.60 and len(top_concerns) < 5:
                    top_concerns.append(f"{metric.name}: {metric.value} — {metric.evidence_text[:80]}")
        # Also include module warnings
        for module in modules:
            for warning in module.warnings:
                if len(top_concerns) < 5:
                    top_concerns.append(warning)

        # 8. Recommendation
        rec, conv = _recommendation(investment_score, confidence_score, risk_score, critical_gaps)

        # 9. LLM synthesis
        executive_summary = None
        if include_llm_synthesis:
            executive_summary = await _synthesize_executive_summary(
                modules, investment_score, rec
            )

        # 10. Sources
        evidence_modules = [m.module_type for m in modules]
        data_sources = list(set(
            src for m in modules for src in m.sources
        ))

        return DecisionOutput(
            investment_score=investment_score,
            confidence_score=round(confidence_score, 2),
            recommendation=rec,
            conviction=conv,
            thesis_score=sub_scores.get("thesis_score", 0),
            financial_score=sub_scores.get("financial_score", 0),
            competitive_score=sub_scores.get("competitive_score", 0),
            market_score=sub_scores.get("market_score", 0),
            valuation_score=sub_scores.get("valuation_score", 0),
            risk_score=risk_score,
            supporting_metrics=supporting,
            contradictory_metrics=contradictory,
            open_questions=open_questions,
            total_metrics=total_metrics,
            module_scores=module_scores,
            top_strengths=top_strengths,
            top_concerns=top_concerns,
            critical_gaps=critical_gaps,
            executive_summary=executive_summary,
            evidence_modules=evidence_modules,
            data_sources=data_sources,
            company_id=self.company_id,
        )
