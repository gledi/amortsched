import { createFileRoute } from "@tanstack/react-router";
import { DashboardPage } from "@/components/DashboardPage";

export const Route = createFileRoute("/_app/")({
  validateSearch: (search: Record<string, unknown>): { compare?: string } => ({
    compare: typeof search.compare === "string" ? search.compare : undefined,
  }),
  component: DashboardPage,
});
