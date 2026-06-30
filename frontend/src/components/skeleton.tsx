export function SkeletonText({ lines = 3, width = "100%" }: { lines?: number; width?: string }) {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-[11px] bg-[#15151f] animate-pulse"
          style={{ width: i === lines - 1 ? "60%" : width }}
        />
      ))}
    </div>
  );
}

export function SkeletonCard({ count = 1 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-[#111118] border border-[#1E1E2E] p-3 animate-pulse">
          <div className="h-4 bg-[#15151f] w-[70%] mb-2" />
          <div className="h-3 bg-[#15151f] w-[40%] mb-3" />
          <div className="h-[1px] bg-[#1E1E2E] my-2" />
          <div className="flex gap-0">
            <div className="flex-1 h-8 bg-[#15151f]" />
            <div className="flex-1 h-8 bg-[#15151f] ml-2" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonMetric({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-3 gap-px bg-[#1E1E2E] border border-[#1E1E2E]">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-[#111118] px-4 py-[15px] animate-pulse">
          <div className="h-3 bg-[#15151f] w-[60%] mb-[7px]" />
          <div className="h-7 bg-[#15151f] w-[50%] mt-[7px]" />
          <div className="h-3 bg-[#15151f] w-[40%] mt-[5px]" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="border border-[#1E1E2E]">
      <div className="grid bg-[#0A0A0F] border-b border-[#1E1E2E] animate-pulse" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="px-3 py-[9px] h-6 bg-[#15151f] m-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="grid border-b border-[#1E1E2E] animate-pulse" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="px-3 py-[10px] h-5 bg-[#15151f] m-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonAgent({ count = 6 }: { count?: number }) {
  return (
    <div className="border border-[#1E1E2E]">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-[11px] px-[13px] py-3 border-b border-[#1E1E2E] animate-pulse">
          <div className="w-[7px] h-[7px] bg-[#15151f] flex-none" />
          <div className="flex-1 min-w-0">
            <div className="h-4 bg-[#15151f] w-[50%] mb-[2px]" />
            <div className="h-3 bg-[#15151f] w-[70%] mt-[2px]" />
          </div>
          <div className="h-5 bg-[#15151f] w-[50px]" />
          <div className="h-5 bg-[#15151f] w-[42px]" />
          <div className="w-6 h-6 bg-[#15151f] flex-none" />
        </div>
      ))}
    </div>
  );
}
