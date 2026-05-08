import type { Stage } from "@/lib/pipeline-data";
import { StageCard } from "./StageCard";
import { PipelineConnector } from "./PipelineConnector";
import type { StageStatus } from "@/lib/pipeline-data";

type ConnectorVariant = "complete" | "to-active" | "active-to-review" | "upcoming";

function getConnectorVariant(from: StageStatus, to: StageStatus): ConnectorVariant {
  if (from === "complete" && to === "complete") return "complete";
  if (from === "complete" && to === "in-progress") return "to-active";
  if (from === "in-progress" && to === "review") return "active-to-review";
  return "upcoming";
}

export function Pipeline({
  stages, activeId, onSelect,
}: {
  stages: Stage[];
  activeId: number;
  onSelect: (id: number) => void;
}) {
  return (
    <div className="relative w-full">
      <div className="relative w-full">
        <div className="flex w-full items-center overflow-x-auto pb-2 pt-1 scrollbar-thin">
          {stages.map((s, i) => {
            const next = stages[i + 1];
            const connectorVariant = next ? getConnectorVariant(s.status, next.status) : undefined;
            return (
              <div key={s.id} className="flex items-center">
                <StageCard stage={s} active={activeId === s.id} onClick={() => onSelect(s.id)} />
                {next && connectorVariant && <PipelineConnector variant={connectorVariant} />}
              </div>
            );
          })}
        </div>
        <div className="pipeline-scroll-fade pointer-events-none absolute bottom-0 right-0 top-0 w-[60px]" />
      </div>
    </div>
  );
}
