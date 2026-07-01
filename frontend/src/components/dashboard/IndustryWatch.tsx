"use client";

interface SectorItem {
  sector: string;
  count: number;
}

interface IndustryWatchProps {
  sectors: SectorItem[];
}

export default function IndustryWatch({ sectors }: IndustryWatchProps) {
  const totalDeals = sectors.reduce((sum, s) => sum + s.count, 0);
  const maxCount = sectors.length > 0 ? Math.max(...sectors.map((s) => s.count)) : 0;

  return (
    <div className="bg-[#111118] border border-[#1E1E2E]">
      <div className="px-4 py-3 border-b border-[#1E1E2E] flex items-center justify-between">
        <div className="text-[13px] font-semibold text-[#E8E8F0]">🏭 Industry Watch</div>
        <div className="font-mono text-[11px] text-[#6B7280]">{totalDeals} deals</div>
      </div>

      <div className="p-4">
        {sectors.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 text-center py-8">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
            <div className="text-[13px] text-[#9aa0ad]">No sector data available.</div>
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {sectors.map((sector) => (
              <div
                key={sector.sector}
                className="bg-[#0A0A0F] border border-[#1E1E2E] p-3 flex flex-col gap-2"
              >
                <div className="text-[11px] text-[#9aa0ad] uppercase tracking-[0.06em]">
                  {sector.sector}
                </div>
                <div className="text-[18px] font-semibold text-[#E8E8F0]">
                  {sector.count}
                </div>
                <div className="w-full h-1 bg-[#1E1E2E] overflow-hidden">
                  <div
                    className="h-full transition-all"
                    style={{
                      width: maxCount > 0 ? `${(sector.count / maxCount) * 100}%` : "0%",
                      backgroundColor: "#C8A96E",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
