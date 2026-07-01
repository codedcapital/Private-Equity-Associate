import React from "react";
import type { ActivityEvent } from "@/types/overview";

interface ActivityFeedItemProps {
  event: ActivityEvent;
}

function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function ActivityFeedItem({ event }: ActivityFeedItemProps) {
  return (
    <div className="flex items-start gap-4 py-3 border-b border-[#1f1f1f] last:border-b-0">
      <span className="font-ov-mono text-xs text-[#525252] shrink-0 w-14 text-right">
        {formatRelativeTime(event.timestamp)}
      </span>
      <div className="flex flex-col gap-0.5 min-w-0">
        <span className="font-ov-sans text-sm text-[#e5e5e5] truncate">
          <span className="text-[#737373]">{event.actor}</span>{" "}
          {event.description}
        </span>
      </div>
    </div>
  );
}
