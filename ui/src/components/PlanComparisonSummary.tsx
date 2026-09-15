import { CircleAlertIcon, EqualIcon, TrophyIcon } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { comparisonHeadline } from "@/lib/comparison-presentation";
import type { PlanComparison } from "@/lib/types";

export function PlanComparisonSummary({ comparison }: { comparison: PlanComparison }) {
  const headline = comparisonHeadline(comparison);
  const tied = comparison.directly_comparable && comparison.overall_winner_plan_ids.length > 1;
  const winner = comparison.directly_comparable && comparison.overall_winner_plan_ids.length === 1;
  const Icon = headline.variant === "destructive" ? CircleAlertIcon : tied ? EqualIcon : TrophyIcon;

  return (
    <Alert variant={winner ? "info" : headline.variant}>
      <Icon />
      <AlertTitle>{headline.title}</AlertTitle>
      <AlertDescription>{headline.description}</AlertDescription>
    </Alert>
  );
}
