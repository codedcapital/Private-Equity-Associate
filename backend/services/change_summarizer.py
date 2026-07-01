"""ChangeSummarizer — Human-readable event summaries and diff rendering.

Transforms raw deal_events into human-readable "Recent Changes" feed.
Supports diff generation between versions of the investment view.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from db.crud import list_deal_events, get_investment_view_by_id
from db.session import async_session_factory

logger = logging.getLogger(__name__)


# ── Diff Helpers ─────────────────────────────────────────────────────────────


def _simple_json_diff(before: dict, after: dict, path: str = "") -> list[dict[str, Any]]:
    """Generate a list of simple diff entries between two JSON objects."""
    changes = []
    all_keys = set(before.keys()) | set(after.keys())
    for key in sorted(all_keys):
        before_val = before.get(key)
        after_val = after.get(key)
        current_path = f"{path}.{key}" if path else key

        if isinstance(before_val, dict) and isinstance(after_val, dict):
            changes.extend(_simple_json_diff(before_val, after_val, current_path))
        elif before_val != after_val:
            changes.append({
                "path": current_path,
                "before": before_val,
                "after": after_val,
            })
    return changes


def _format_diff_for_display(diff: list[dict], label_map: dict[str, str] | None = None) -> list[str]:
    """Convert raw diff entries to human-readable strings."""
    label_map = label_map or {
        "content": "Investment View Content",
        "content.text": "View Text",
        "recommendation": "Recommendation",
        "confidence_score": "Confidence Score",
        "status": "Status",
    }
    lines = []
    for d in diff:
        path = d["path"]
        label = label_map.get(path, path.replace(".", " ").title())
        before = d["before"]
        after = d["after"]

        if before is None and after is not None:
            lines.append(f"{label} set to {after}")
        elif before is not None and after is None:
            lines.append(f"{label} removed (was {before})")
        else:
            lines.append(f"{label} changed from {before} → {after}")
    return lines


# ── ChangeSummarizer ─────────────────────────────────────────────────────────


class ChangeSummarizer:
    """Summarizes deal events into human-readable change descriptions."""

    EVENT_TEMPLATES: dict[str, str] = {
        "view_updated": "{actor} updated the investment view — {details}",
        "evidence_refreshed": "Evidence refreshed — {details}",
        "diligence_status_changed": "Diligence item {details}",
        "confidence_recalculated": "Confidence score {details}",
        "recommendation_changed": "Recommendation changed to {details}",
        "stage_changed": "Deal stage moved to {details}",
    }

    def __init__(self, deal_id: int):
        self.deal_id = deal_id

    async def summarize_recent(self, limit: int = 20, time_window_hours: int = 168) -> list[dict[str, Any]]:
        """Generate human-readable summaries of recent events.

        Args:
            limit: Max number of events to return.
            time_window_hours: Only include events within this many hours.

        Returns:
            List of summarized change dicts with id, timestamp, description, type, actor, metadata.
        """
        async with async_session_factory() as session:
            events = await list_deal_events(session, deal_id=self.deal_id, limit=limit)
            cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=time_window_hours)

            summaries = []
            for event in events:
                if event.created_at and event.created_at < cutoff:
                    continue

                summary = self._summarize_event(event)
                summaries.append(summary)

            return summaries

    def _summarize_event(self, event: Any) -> dict[str, Any]:
        """Summarize a single deal event into a human-readable dict."""
        event_type = event.event_type
        actor = event.actor_id or event.actor_type or "System"
        metadata = event.event_metadata or {}

        description = event.description
        details = ""

        # Build details from metadata
        if event_type == "view_updated":
            diff = metadata
            if "content_changed" in diff:
                details = "content updated"
            if "recommendation_changed" in diff:
                rec = diff["recommendation_changed"]
                details = f"recommendation changed from {rec.get('from')} to {rec.get('to')}"
            if "confidence_changed" in diff:
                conf = diff["confidence_changed"]
                old_v = conf.get("from")
                new_v = conf.get("to")
                if old_v is not None and new_v is not None:
                    direction = "increased" if new_v > old_v else "decreased"
                    details = f"confidence {direction} from {old_v}% to {new_v}%"
            if not details:
                details = "new version created"
            description = f"{actor} updated investment view — {details}"

        elif event_type == "diligence_status_changed":
            item_meta = metadata
            if "from" in item_meta and "to" in item_meta:
                description = f"Diligence '{item_meta.get('item_title', 'item')}' status changed from {item_meta['from']} to {item_meta['to']}"
            elif "item_id" in item_meta:
                description = f"Diligence item updated (ID: {item_meta['item_id']})"
            else:
                description = event.description

        elif event_type == "confidence_recalculated":
            old_score = metadata.get("old_score")
            new_score = metadata.get("new_score")
            if old_score is not None and new_score is not None:
                direction = "increased" if new_score > old_score else "decreased"
                description = f"Investment confidence {direction} from {old_score}% to {new_score}%"
            else:
                description = event.description

        elif event_type == "evidence_refreshed":
            source = metadata.get("source", "intelligence engine")
            description = f"Evidence refreshed from {source}"
            if "module" in metadata:
                description += f" — {metadata['module']} module"

        elif event_type == "evidence_status_changed":
            evidence_id = metadata.get("evidence_id")
            old_status = metadata.get("old_status")
            new_status = metadata.get("new_status")
            if evidence_id and old_status and new_status:
                description = f"Evidence item #{evidence_id} status changed from {old_status} to {new_status}"
            else:
                description = event.description

        elif event_type == "recommendation_changed":
            old_rec = metadata.get("from")
            new_rec = metadata.get("to")
            if old_rec and new_rec:
                description = f"Recommendation changed from {old_rec} to {new_rec}"
            else:
                description = event.description

        elif event_type == "stage_changed":
            old_stage = metadata.get("from")
            new_stage = metadata.get("to")
            if old_stage and new_stage:
                description = f"Deal stage moved from {old_stage} to {new_stage}"
            else:
                description = event.description

        return {
            "id": event.id,
            "timestamp": event.created_at.isoformat() if event.created_at else None,
            "event_type": event_type,
            "actor": actor,
            "description": description,
            "metadata": metadata,
            "diff": metadata,
        }

    async def diff_investment_views(self, from_version_id: int, to_version_id: int) -> dict[str, Any]:
        """Generate a diff between two versions of an investment view.

        Returns:
            dict with changes list, summary, and raw before/after.
        """
        async with async_session_factory() as session:
            from_view = await get_investment_view_by_id(session, from_version_id)
            to_view = await get_investment_view_by_id(session, to_version_id)

            if not from_view or not to_view:
                raise ValueError("One or both investment view versions not found")

            before = {
                "content": from_view.content,
                "recommendation": from_view.recommendation,
                "confidence_score": from_view.confidence_score,
                "status": from_view.status,
            }
            after = {
                "content": to_view.content,
                "recommendation": to_view.recommendation,
                "confidence_score": to_view.confidence_score,
                "status": to_view.status,
            }

            raw_diff = _simple_json_diff(before, after)
            display_lines = _format_diff_for_display(raw_diff)

            return {
                "from_version": from_view.version,
                "to_version": to_view.version,
                "from_id": from_view.id,
                "to_id": to_view.id,
                "changes": raw_diff,
                "summary": display_lines,
                "before": before,
                "after": after,
            }
