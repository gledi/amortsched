import { describe, expect, it } from "vitest";
import { makeComparison, makeComparisonItem } from "@/test/fixtures";
import type { PlanComparison, PlanComparisonItem } from "./types";
import { comparisonHeadline, crossoverMonth, horizonHeadline } from "./comparison-presentation";

const plan: PlanComparisonItem = makeComparisonItem();
const comparison: PlanComparison = makeComparison({
  overall_winner_plan_ids: ["union"],
  savings_vs_next_best: "18870.00",
  plans: [plan, { ...plan, id: "other", name: "Other offer", lender: null, total_cost: "470370" }],
});

describe("comparisonHeadline", () => {
  it("describes a unique winner and savings", () => {
    expect(comparisonHeadline(comparison)).toEqual({
      title: "Union Bank has the lowest total cost",
      description: "Saves $18,870.00 versus the next-lowest offer, including fees and PMI.",
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
    expect(headline.description).toBe("Saves $12.34 versus the next-lowest offer, including fees and PMI.");
  });
});

describe("horizonHeadline", () => {
  it("names the cheapest offer at the horizon and the saving", () => {
    const headline = horizonHeadline(
      makeComparison({
        horizon_months: 60,
        horizon_winner_plan_ids: ["union"],
        plans: [
          makeComparisonItem({ horizon: { months: 60, cost: "1000", balance: "0", payoff_penalty: "0" } }),
          makeComparisonItem({
            id: "other",
            lender: null,
            name: "Other",
            horizon: { months: 60, cost: "1250", balance: "0", payoff_penalty: "0" },
          }),
        ],
      }),
    );
    expect(headline).toBe("If you sell or refinance after 5 yrs, Union Bank costs least, saving $250.00.");
  });

  it("is silent without a horizon", () => {
    expect(horizonHeadline(makeComparison())).toBeNull();
  });
});

describe("crossoverMonth", () => {
  it("finds where the cheaper offer changes", () => {
    const fees = makeComparisonItem({ cumulative_cost: ["100", "101", "102", "103"] });
    const rate = makeComparisonItem({ id: "rate", cumulative_cost: ["0", "40", "80", "120"] });
    expect(crossoverMonth(fees, rate)).toBe(3);
    expect(crossoverMonth(fees, fees)).toBeNull();
  });
});
