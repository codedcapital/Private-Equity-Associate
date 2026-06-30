export default function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-[18px] px-5 py-[60px] border border-dashed border-[#1E1E2E]">
      {icon && (
        <div className="relative w-16 h-16 flex items-center justify-center">
          <div className="absolute inset-0 border border-[#1E1E2E] rounded-full" />
          <div className="absolute inset-3 border border-[#1E1E2E] rounded-full animate-pePulse" />
          <div className="text-[#C8A96E]">{icon}</div>
        </div>
      )}
      <div className="text-center">
        <div className="text-sm text-[#9aa0ad]">{title}</div>
        {description && (
          <div className="mt-[6px] font-mono text-[11px] text-[#4b5160]">{description}</div>
        )}
      </div>
      {action}
    </div>
  );
}
