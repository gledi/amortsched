import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_app/compare")({
  validateSearch: (search: Record<string, unknown>) => ({
    plans: typeof search.plans === "string" ? search.plans : undefined,
  }),
  component: CompareRoute,
});

function CompareRoute() {
  return null;
}
