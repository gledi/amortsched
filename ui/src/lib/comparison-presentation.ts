import { formatCurrency, formatMonths } from "./formatters";
import type { PlanComparison, PlanComparisonItem } from "./types";

export const SERIES_COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)"] as const;

export function offerLabel(plan: Pick<PlanComparisonItem, "lender" | "name">): string {
  return plan.lender || plan.name;
}

export function chartLabel(plan: Pick<PlanComparisonItem, "lender" | "name">): string {
  return plan.lender ? `${plan.lender} — ${plan.name}` : plan.name;
}

export function comparisonCurrency(comparison: PlanComparison): string | null {
  const currencies = new Set(comparison.plans.map((plan) => plan.currency));
  return currencies.size === 1 ? comparison.plans[0].currency : null;
}

export function horizonHeadline(comparison: PlanComparison): string | null {
  if (comparison.horizon_months === null || comparison.horizon_winner_plan_ids.length === 0) return null;
  const period = formatMonths(comparison.horizon_months);
  const winners = comparison.plans.filter((plan) => comparison.horizon_winner_plan_ids.includes(plan.id));
  if (winners.length > 1) return `If you sell or refinance after ${period}, ${winners.length} offers cost the same.`;
  const winner = winners[0];
  const others = comparison.plans.filter((plan) => plan.id !== winner.id && plan.horizon !== null);
  const nextCost = Math.min(...others.map((plan) => Number(plan.horizon?.cost)));
  const saving = Number.isFinite(nextCost) ? nextCost - Number(winner.horizon?.cost) : null;
  const savingText = saving !== null && saving > 0 ? `, saving ${formatCurrency(saving, winner.currency)}` : "";
  return `If you sell or refinance after ${period}, ${offerLabel(winner)} costs least${savingText}.`;
}

/** First month after which `a` stays cheaper than `b` for good, or null if the lead never changes. */
export function crossoverMonth(a: PlanComparisonItem, b: PlanComparisonItem): number | null {
  const length = Math.max(a.cumulative_cost.length, b.cumulative_cost.length);
  const at = (series: (string | number)[], index: number) => Number(series[Math.min(index, series.length - 1)]);
  const leadAtStart = Math.sign(at(a.cumulative_cost, 0) - at(b.cumulative_cost, 0));
  for (let month = 1; month < length; month += 1) {
    const lead = Math.sign(at(a.cumulative_cost, month) - at(b.cumulative_cost, month));
    if (lead !== 0 && lead !== leadAtStart) return month;
  }
  return null;
}

export function comparisonHeadline(comparison: PlanComparison): {
  title: string;
  description: string;
  variant: "default" | "destructive";
} {
  if (!comparison.directly_comparable) {
    return {
      title: "These offers are not directly comparable",
      description: `${comparison.incomparability_reasons.length > 0 ? comparison.incomparability_reasons.map((reason) => (reason.endsWith(".") ? reason : `${reason}.`)).join(" ") : "Principal amounts differ."} Review individual metrics before deciding.`,
      variant: "destructive",
    };
  }

  const winnerIds = comparison.overall_winner_plan_ids;
  if (winnerIds.length > 1) {
    const count = ({ 2: "Two", 3: "Three", 4: "Four" } as Record<number, string>)[winnerIds.length] ?? winnerIds.length;
    return {
      title: `${count} offers tie for the lowest total cost`,
      description: "Review the payment, fees, and payoff timing to choose the offer that fits you.",
      variant: "default",
    };
  }

  const winner = comparison.plans.find((plan) => plan.id === winnerIds[0]);
  if (!winner) {
    return {
      title: "Review your loan offers",
      description: "Compare the payment, fees, and payoff timing for each offer.",
      variant: "default",
    };
  }
  return {
    title: `${winner.lender || winner.name} has the lowest total cost`,
    description:
      comparison.savings_vs_next_best === null
        ? "Review the payment, fees, and payoff timing to choose the offer that fits you."
        : `Saves ${formatCurrency(comparison.savings_vs_next_best, winner.currency)} versus the next-lowest offer, including fees and PMI.`,
    variant: "default",
  };
}
