import { useMemo } from "react";
import type { RequirementStatus } from "@/lib/requirements-data";

export type HealthSegment = {
  key: RequirementStatus;
  label: string;
  value: number;
  color: string;
};

export function PipelineHealth({
  segments,
  activeFilter,
  onToggleFilter,
}: {
  segments: HealthSegment[];
  activeFilter: RequirementStatus | null;
  onToggleFilter: (key: RequirementStatus) => void;
}) {
  const total = segments.reduce((s, x) => s + x.value, 0);

  // donut math
  const size = 80;
  const stroke = 12;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const C = 2 * Math.PI * r;
  const gap = 2;

  const arcs = useMemo(() => {
    let cumulative = 0;
    return segments.map((seg) => {
      const frac = total > 0 ? seg.value / total : 0;
      const length = Math.max(0, frac * C - gap);
      const offset = C / 4 - cumulative * C;
      cumulative += frac;
      return { ...seg, length, offset };
    });
  }, [segments, total, C]);

  return (
    <div
      className="flex h-full items-center gap-[14px] bg-white px-5 py-3"
      style={{
        borderRadius: 12,
        border: "1px solid #e2e4ef",
      }}
    >
      {/* Donut */}
      <div
        className="relative shrink-0 cursor-pointer transition-transform duration-200 hover:scale-110"
        style={{ width: size, height: size }}
        onClick={() => {
          if (activeFilter) onToggleFilter(activeFilter);
        }}
        title={activeFilter ? "Clear filter" : "Click a segment to filter"}
      >
        <svg viewBox={`0 0 ${size} ${size}`} className="h-full w-full overflow-visible">
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f1f2f7" strokeWidth={stroke} />
          {arcs.map((a) => {
            const isError = a.key === "error";
            const isActive = activeFilter === a.key;
            return (
              <circle
                key={a.key}
                cx={cx}
                cy={cy}
                r={r}
                fill="none"
                stroke={a.color}
                strokeWidth={isActive ? stroke + 3 : stroke}
                strokeDasharray={`${a.length} ${C}`}
                strokeDashoffset={a.offset}
                style={{ cursor: "pointer", transition: "stroke-width 200ms" }}
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleFilter(a.key);
                }}
                className={isError && a.value > 0 ? "animate-pulse-segment" : ""}
              />
            );
          })}
        </svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[22px] font-bold leading-none text-[#1f2330]">{total}</span>
          <span className="mt-0.5 text-[9px] font-medium uppercase tracking-wider text-[#8a8f9c]">items</span>
        </div>
      </div>

      {/* Legend pills */}
      <div className="flex flex-1 items-stretch gap-2">
        {(() => {
          const allActive = activeFilter === null;
          return (
            <button
              type="button"
              onClick={() => activeFilter && onToggleFilter(activeFilter)}
              className="flex items-center justify-center gap-2 rounded-full border px-3 py-2 text-[12px] font-medium transition-all hover:scale-[1.03] hover:shadow-sm"
              style={{
                borderColor: allActive ? "#1f2330" : "#e2e4ef",
                backgroundColor: allActive ? "#1f23301a" : "#ffffff",
                color: allActive ? "#1f2330" : "#4a5068",
                borderWidth: allActive ? 1.5 : 1,
              }}
            >
              <span className="whitespace-nowrap">All</span>
              <span className="font-mono tabular-nums">{total}</span>
            </button>
          );
        })()}
        {segments.map((s) => {
          const active = activeFilter === s.key;
          return (
            <button
              key={s.key}
              type="button"
              onClick={() => onToggleFilter(s.key)}
              className="flex flex-1 items-center justify-center gap-2 rounded-full border px-3 py-2 text-[12px] font-medium transition-all hover:scale-[1.03] hover:shadow-sm"
              style={{
                borderColor: active ? s.color : "#e2e4ef",
                backgroundColor: active ? `${s.color}1a` : "#ffffff",
                color: active ? s.color : "#4a5068",
                borderWidth: active ? 1.5 : 1,
              }}
            >
              <span
                className="rounded-full"
                style={{ backgroundColor: s.color, width: 8, height: 8 }}
              />
              <span className="whitespace-nowrap">{s.label}</span>
              <span className="font-mono tabular-nums">{s.value}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
