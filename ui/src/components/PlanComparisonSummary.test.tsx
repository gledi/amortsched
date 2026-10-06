import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { makeComparison, makeComparisonItem } from "@/test/fixtures";
import type { PlanComparison, PlanComparisonItem } from "@/lib/types";
import { PlanComparisonSummary } from "./PlanComparisonSummary";

const plan: PlanComparisonItem = makeComparisonItem();
const comparison: PlanComparison = makeComparison({
  overall_winner_plan_ids: ["union"],
  savings_vs_next_best: "18870.00",
  plans: [plan, { ...plan, id: "other", name: "Other offer", lender: null }],
});

describe("PlanComparisonSummary", () => {
  afterEach(cleanup);
  it("shows the unique winner and backend savings", () => {
    render(<PlanComparisonSummary comparison={comparison} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Union Bank has the lowest total cost");
    expect(screen.getByText("Saves $18,870.00 versus the next-lowest offer, including fees and PMI.")).toBeVisible();
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
