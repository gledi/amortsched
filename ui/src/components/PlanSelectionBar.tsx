import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

interface PlanSelectionBarProps {
  selectedCount: number;
  limitReached: boolean;
  removedCount?: number;
  onCancel: () => void;
  onCompare: () => void;
}

export function PlanSelectionBar({
  selectedCount,
  limitReached,
  removedCount = 0,
  onCancel,
  onCompare,
}: PlanSelectionBarProps) {
  return (
    <div className="sticky bottom-4 z-10 flex flex-col gap-2 border border-border bg-background p-3 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-medium">
          {selectedCount} {selectedCount === 1 ? "plan" : "plans"} selected
        </p>
        {removedCount > 0 ? (
          <Alert variant="info">
            <AlertDescription>
              Removed {removedCount} invalid, unavailable, or excess selections. Choose 2 to 4 available plans.
            </AlertDescription>
          </Alert>
        ) : null}
        {limitReached ? (
          <Alert variant="info">
            <AlertDescription>You can compare up to 4 plans.</AlertDescription>
          </Alert>
        ) : null}
      </div>
      <div className="flex items-center gap-2">
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button disabled={selectedCount < 2 || selectedCount > 4} onClick={onCompare}>
          Compare
        </Button>
      </div>
    </div>
  );
}
