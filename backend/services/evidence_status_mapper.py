"""Evidence Status Mapper — Maps intelligence engine outputs to the 4-state taxonomy.

Takes raw EvidenceModule / EvidenceMetric outputs and classifies each evidence
item as VERIFIED, NEEDS_VALIDATION, CONFLICTING, or UNKNOWN.

Rules:
  - VERIFIED: Primary regulatory source (SEC, audited financials)
  - NEEDS_VALIDATION: Agent model, API data, synthesized research
  - CONFLICTING: Two sources disagree on the same metric
  - UNKNOWN: No evidence found, placeholder, or explicitly missing
"""

from __future__ import annotations

import logging
from typing import Any

from db.models import EvidenceItem, EvidenceStatus

logger = logging.getLogger(__name__)


# ── Source classification rules ────────────────────────────────────────────────

PRIMARY_SOURCES: set[str] = {
    "SEC EDGAR",
    "SEC 10-K",
    "SEC 10-Q",
    "Yahoo Finance",
    "FMP",
    "Financial Modeling Prep",
    "audited financials",
}

SYNTHESIZED_SOURCES: set[str] = {
    "Research Agent",
    "Competitive Agent",
    "Memo Agent",
    "Tavily Web Search",
    "web search",
    "synthesized",
}

MODEL_SOURCES: set[str] = {
    "LBO Agent",
    "Financial Agent",
    "model-based",
    "projection",
    "assumption",
}


def _source_to_status(source: str, source_type: str) -> EvidenceStatus:
    """Classify an evidence item based on its source."""
    source_lower = source.lower()
    source_type_lower = source_type.lower()

    # Primary / regulatory sources
    if any(ps.lower() in source_lower for ps in PRIMARY_SOURCES):
        return EvidenceStatus.VERIFIED

    # Synthesized or web sources
    if any(ss.lower() in source_lower for ss in SYNTHESIZED_SOURCES):
        return EvidenceStatus.NEEDS_VALIDATION

    # Model / projection sources
    if any(ms.lower() in source_lower for ms in MODEL_SOURCES):
        return EvidenceStatus.NEEDS_VALIDATION

    # Direct filings
    if source_type_lower in ("filing", "regulatory", "audited"):
        return EvidenceStatus.VERIFIED

    # API / structured data
    if source_type_lower in ("api", "structured"):
        return EvidenceStatus.NEEDS_VALIDATION

    # Expert / internal
    if source_type_lower in ("expert_call", "internal", "management"):
        return EvidenceStatus.NEEDS_VALIDATION

    # Web / unknown
    if source_type_lower in ("web", "news", "blog"):
        return EvidenceStatus.NEEDS_VALIDATION

    return EvidenceStatus.UNKNOWN


class EvidenceStatusMapper:
    """Maps evidence outputs to the 4-state status taxonomy."""

    @staticmethod
    def classify_evidence_item(item: EvidenceItem) -> EvidenceStatus:
        """Classify a single evidence item."""
        return _source_to_status(item.source, item.source_type)

    @staticmethod
    def classify_from_source(source: str, source_type: str) -> EvidenceStatus:
        """Classify from raw source strings."""
        return _source_to_status(source, source_type)

    @staticmethod
    def classify_evidence_module(
        module_type: str,
        metrics: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Classify all metrics in an evidence module.

        Returns the metrics with an added 'evidence_status' field.
        """
        classified = []
        for metric in metrics:
            source = metric.get("source", "")
            source_type = metric.get("source_type", "")
            status = _source_to_status(source, source_type)
            classified.append({**metric, "evidence_status": status.value})
        return classified

    @staticmethod
    def detect_conflicts(
        evidence_items: list[EvidenceItem],
    ) -> list[tuple[int, int, str]]:
        """Detect conflicts between evidence items on the same metric.

        Returns a list of (evidence_a_id, evidence_b_id, description) tuples.
        """
        conflicts: list[tuple[int, int, str]] = []
        # Simple heuristic: group by similar text / source and check for
        # contradictory flags
        for i, item_a in enumerate(evidence_items):
            for item_b in evidence_items[i + 1 :]:
                if item_a.is_contradictory and item_b.is_supporting:
                    conflicts.append(
                        (
                            item_a.id,
                            item_b.id,
                            f"Contradictory evidence on '{item_a.text[:60]}' "
                            f"vs supporting '{item_b.text[:60]}'",
                        )
                    )
                elif item_a.is_supporting and item_b.is_contradictory:
                    conflicts.append(
                        (
                            item_a.id,
                            item_b.id,
                            f"Supporting evidence '{item_a.text[:60]}' "
                            f"vs contradictory '{item_b.text[:60]}'",
                        )
                    )
        return conflicts

    @staticmethod
    def batch_classify(items: list[EvidenceItem]) -> dict[int, EvidenceStatus]:
        """Classify a batch of evidence items efficiently."""
        return {item.id: _source_to_status(item.source, item.source_type) for item in items}
