import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { PlanComparison, PlanComparisonItem } from "@/lib/types";
import { PlanComparisonSummary } from "./PlanComparisonSummary";

const plan: PlanComparisonItem = {
  id: "union",
  name: "Union offer",
  lender: "Union Bank",
  principal: "250000",
  interest_rate: "4.5",
  term: { years: 30, months: 0 },
  start_date: "2026-01-01",
  starting_monthly_payment: "1266.71",
  configured_early_payment_fees: { fixed: "0", percent: "0" },
  upfront_fees: "1500",
  total_principal: "250000",
  total_interest: "200000",
  schedule_fees: "0",
  schedule_total_outflow: "450000",
  total_cost: "451500",
  payoff_months: 360,
  payoff_month: "2055-12",
  paid_off: true,
  adjustment_counts: { one_time_extra_payments: 0, recurring_extra_payments: 0, interest_rate_changes: 0 },
};
const comparison: PlanComparison = {
  directly_comparable: true,
  incomparability_reasons: [],
  overall_winner_plan_ids: ["union"],
  savings_vs_next_best: "18870.00",
  best_plan_ids_by_metric: {},
  plans: [plan, { ...plan, id: "other", name: "Other offer", lender: null }],
};

describe("PlanComparisonSummary", () => {
  afterEach(cleanup);
  it("shows the unique winner and backend savings", () => {
    render(<PlanComparisonSummary comparison={comparison} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Union Bank has the lowest total cost");
    expect(screen.getByText("Saves $18,870.00 versus the next-lowest offer.")).toBeVisible();
  });
  it("warns when the principal amounts differ", () => {
    render(<PlanComparisonSummary comparison={{ ...comparison, directly_comparable: false }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("These offers are not directly comparable");
    expect(screen.getByText("Principal amounts differ. Review individual metrics before deciding.")).toBeVisible();
  });
  it("gives tied offers a neutral summary without a savings claim", () => {
    render(
      <PlanComparisonSummary
        comparison={{ ...comparison, overall_winner_plan_ids: ["union", "other"], savings_vs_next_best: null }}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Two offers tie for the lowest total cost");
    expect(
      screen.getByText("Review the payment, fees, and payoff timing to choose the offer that fits you."),
    ).toBeVisible();
    expect(screen.getByRole("alert")).not.toHaveTextContent("Saves");
  });
});
