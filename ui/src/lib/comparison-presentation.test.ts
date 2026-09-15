import { describe, expect, it } from "vitest";
import type { PlanComparison, PlanComparisonItem } from "./types";
import { comparisonHeadline } from "./comparison-presentation";

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
  plans: [plan, { ...plan, id: "other", name: "Other offer", lender: null, total_cost: "470370" }],
};

describe("comparisonHeadline", () => {
  it("describes a unique winner and savings", () => {
    expect(comparisonHeadline(comparison)).toEqual({
      title: "Union Bank has the lowest total cost",
      description: "Saves $18,870.00 versus the next-lowest offer.",
      variant: "default",
    });
  });
  it("does not claim a winner for different principals", () => {
    expect(
      comparisonHeadline({
        ...comparison,
        directly_comparable: false,
        incomparability_reasons: ["Principal amounts differ"],
      }),
    ).toEqual({
      title: "These offers are not directly comparable",
      description: "Principal amounts differ. Review individual metrics before deciding.",
      variant: "destructive",
    });
  });
  it("describes tied winners without a savings claim", () => {
    const headline = comparisonHeadline({
      ...comparison,
      overall_winner_plan_ids: ["union", "other"],
      savings_vs_next_best: null,
    });
    expect(headline.title).toBe("Two offers tie for the lowest total cost");
    expect(headline.description).not.toContain("Saves");
  });
  it("uses backend winner IDs even when another displayed cost is lower", () => {
    const headline = comparisonHeadline({
      ...comparison,
      overall_winner_plan_ids: ["other"],
      savings_vs_next_best: "12.34",
    });
    expect(headline.title).toBe("Other offer has the lowest total cost");
    expect(headline.description).toBe("Saves $12.34 versus the next-lowest offer.");
  });
});
