import { formatCurrency } from "./formatters";
import type { PlanComparison } from "./types";

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
        : `Saves ${formatCurrency(comparison.savings_vs_next_best)} versus the next-lowest offer.`,
    variant: "default",
  };
}
