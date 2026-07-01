"use client";

import React from "react";
import { ArrowRight } from "lucide-react";
import type { ActivityEvent } from "@/types/overview";
import { ActivityFeedItem } from "@/components/overview/primitives/activity-feed-item";
import { SectionHeader } from "@/components/overview/primitives/section-header";
import { SkeletonSection } from "@/components/overview/primitives/skeleton-section";

interface RecentChangesSectionProps {
  activity: ActivityEvent[];
  loading?: boolean;
}

export function RecentChangesSection({ activity, loading }: RecentChangesSectionProps) {
  const recent = activity.slice(0, 10);

  if (loading) {
    return (
      <section>
        <SectionHeader title="Recent Changes" />
        <div className="border border-[#1f1f1f] bg-[#141414] rounded-sm">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="px-4 py-3 border-b border-[#1f1f1f] last:border-b-0">
              <SkeletonSection lines={1} hasHeader={false} />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (activity.length === 0) {
    return (
      <section>
        <SectionHeader title="Recent Changes" />
        <div className="p-6 border border-[#1f1f1f] bg-[#141414] rounded-sm">
          <p className="font-ov-sans text-sm text-[#737373]">No recent activity.</p>
        </div>
      </section>
    );
  }

  return (
    <section>
      <SectionHeader title="Recent Changes" />
      <div className="border border-[#1f1f1f] bg-[#141414] rounded-sm">
        {recent.map((event) => (
          <ActivityFeedItem key={event.id} event={event} />
        ))}
      </div>

      <button
        disabled
        className="flex items-center gap-1.5 mt-4 text-xs font-ov-sans font-medium text-[#525252] hover:text-[#737373] transition-colors cursor-not-allowed"
      >
        View All
        <ArrowRight className="w-3.5 h-3.5" />
      </button>
    </section>
  );
}
