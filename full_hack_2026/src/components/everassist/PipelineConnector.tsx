import { cn } from "@/lib/utils";

export function PipelineConnector({
  variant,
}: {
  variant: "complete" | "to-active" | "active-to-review" | "upcoming";
}) {
  const isComplete = variant === "complete";
  const isToActive = variant === "to-active";
  const isActiveToReview = variant === "active-to-review";
  const isUpcoming = variant === "upcoming";

  return (
    <div className="relative flex h-12 w-16 shrink-0 items-center justify-center">
      <svg viewBox="0 0 64 12" className="h-3 w-full overflow-visible" preserveAspectRatio="none">
        <line
          x1="0" y1="6" x2="64" y2="6"
          stroke="currentColor"
          strokeWidth="2"
          className={cn(
            isComplete && "text-[#16A34A]",
            isToActive && "text-[#2563EB]",
            isActiveToReview && "text-[#D97706]",
            isUpcoming && "text-[#D1D5DB]",
          )}
          strokeDasharray={isUpcoming ? "4 4" : undefined}
        />
        {isActiveToReview && (
          <line
            x1="0" y1="6" x2="64" y2="6"
            stroke="#D97706"
            strokeWidth="1.5"
            strokeDasharray="10 8"
            strokeLinecap="round"
            className="animate-[connector-dash_1.6s_linear_infinite]"
          />
        )}
        <polygon
          points="60,2 64,6 60,10"
          className={cn(
            isComplete && "fill-[#16A34A]",
            isToActive && "fill-[#2563EB]",
            isActiveToReview && "fill-[#D97706]",
            isUpcoming && "fill-[#D1D5DB]",
          )}
        />
      </svg>
    </div>
  );
}
