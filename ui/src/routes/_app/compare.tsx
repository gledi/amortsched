import { createFileRoute, redirect } from "@tanstack/react-router";
import { ComparePage } from "@/components/ComparePage";
import { isComparableSelection, isPlanId, parsePlanIds } from "@/lib/plan-selection";

export const Route = createFileRoute("/_app/compare")({
  validateSearch: (search: Record<string, unknown>): { plans?: string; horizon?: number } => {
    const horizon = Number(search.horizon);
    return {
      plans: typeof search.plans === "string" ? search.plans : undefined,
      horizon: Number.isInteger(horizon) && horizon >= 1 && horizon <= 50 ? horizon : undefined,
    };
  },
  beforeLoad: ({ search }) => {
    const planIds = parsePlanIds(search.plans);
    if (!isComparableSelection(planIds) || planIds.some((id) => !isPlanId(id))) {
      throw redirect({ to: "/", search: { compare: planIds.join(",") }, replace: true });
    }
  },
  component: ComparePage,
});
