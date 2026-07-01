"use client";

interface PipelineStage {
  name: string;
  count: number;
  color: string;
}

interface PipelineMiniChartProps {
  stages: PipelineStage[];
}

export default function PipelineMiniChart({ stages }: PipelineMiniChartProps) {
  const maxCount = Math.max(...stages.map((s) => s.count), 1);

  return (
    <div className="bg-[#111118] border border-[#1E1E2E] p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[13px] font-semibold text-[#E8E8F0]">Pipeline Overview</div>
        <a
          href="/pipeline"
          className="text-[11px] text-[#2DD4BF] hover:text-[#2DD4BF]/80 transition-colors font-medium"
        >
          View Pipeline →
        </a>
      </div>
      <div className="flex flex-col gap-2">
        {stages.map((stage) => (
          <div key={stage.name} className="flex items-center gap-3">
            <span className="w-[100px] text-[11px] text-[#9aa0ad] font-medium truncate">
              {stage.name}
            </span>
            <div className="flex-1 h-[8px] bg-[#0A0A0F] overflow-hidden">
              <div
                className="h-full"
                style={{
                  width: `${(stage.count / maxCount) * 100}%`,
                  backgroundColor: stage.color,
                }}
              />
            </div>
            <span className="w-[24px] text-right font-mono text-[11px] text-[#E8E8F0]">
              {stage.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
