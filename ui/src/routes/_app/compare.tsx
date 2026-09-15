import { createFileRoute, redirect } from "@tanstack/react-router";
import { ComparePage } from "@/components/ComparePage";
import { isComparableSelection, isPlanId, parsePlanIds } from "@/lib/plan-selection";

export const Route = createFileRoute("/_app/compare")({
  validateSearch: (search: Record<string, unknown>): { plans?: string } => ({
    plans: typeof search.plans === "string" ? search.plans : undefined,
  }),
  beforeLoad: ({ search }) => {
    const planIds = parsePlanIds(search.plans);
    if (!isComparableSelection(planIds) || planIds.some((id) => !isPlanId(id))) {
      throw redirect({ to: "/", search: { compare: planIds.join(",") }, replace: true });
    }
  },
  component: ComparePage,
});
