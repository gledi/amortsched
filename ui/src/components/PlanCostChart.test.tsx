import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { PlanComparisonItem } from "@/lib/types";
import { PlanCostChart } from "./PlanCostChart";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("distinguishes offers from the same lender on the cost chart", async () => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
    return this.classList.contains("recharts-responsive-container")
      ? new DOMRect(0, 0, 960, 320)
      : new DOMRect(0, 0, (this.textContent?.length ?? 0) * 7, 16);
  });
  const plan: PlanComparisonItem = {
    id: "first",
    name: "Fixed offer",
    lender: "Shared Bank",
    principal: "1200",
    interest_rate: "3",
    term: { years: 1, months: 0 },
    start_date: "2026-01-01",
    starting_monthly_payment: "102",
    configured_early_payment_fees: { fixed: "0", percent: "0" },
    upfront_fees: "10",
    total_principal: "1200",
    total_interest: "24",
    schedule_fees: "0",
    schedule_total_outflow: "1224",
    total_cost: "1234",
    payoff_months: 12,
    payoff_month: "2026-12",
    paid_off: true,
    adjustment_counts: { one_time_extra_payments: 0, recurring_extra_payments: 0, interest_rate_changes: 0 },
  };
  render(
    <PlanCostChart
      comparison={{
        directly_comparable: true,
        incomparability_reasons: [],
        overall_winner_plan_ids: [],
        savings_vs_next_best: null,
        best_plan_ids_by_metric: {},
        plans: [plan, { ...plan, id: "second", name: "Flexible offer" }],
      }}
    />,
  );
  expect(await screen.findByText("Shared Bank — Fixed offer")).toBeInTheDocument();
  expect(screen.getByText("Shared Bank — Flexible offer")).toBeInTheDocument();
});
