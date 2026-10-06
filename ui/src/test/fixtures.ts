import type { Plan, PlanComparison, PlanComparisonItem } from "@/lib/types";

export function makePlan(overrides: Partial<Plan> = {}): Plan {
  return {
    id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    user_id: "owner",
    name: "Offer",
    slug: "offer",
    amount: "1200",
    interest_rate: "3",
    term: { years: 1, months: 0 },
    start_date: "2026-01-01",
    loan_type: "other",
    currency: "USD",
    lender: null,
    upfront_fees: "0",
    early_payment_fees: { fixed: "0", percent: "0" },
    housing_costs: {
      property_value: null,
      property_tax_annual: "0",
      insurance_annual: "0",
      hoa_monthly: "0",
      pmi_annual_rate: "0",
      pmi_cancel_ltv: "78",
    },
    down_payment: null,
    ltv: null,
    monthly_payment: "101.63",
    monthly_housing: null,
    interest_rate_application: "whole_month",
    status: "draft",
    one_time_extra_payments: [],
    recurring_extra_payments: [],
    interest_rate_changes: [],
    created_at: "2026-01-01",
    updated_at: "2026-01-01",
    ...overrides,
  };
}

export function makeComparisonItem(overrides: Partial<PlanComparisonItem> = {}): PlanComparisonItem {
  return {
    id: "union",
    name: "Union offer",
    lender: "Union Bank",
    currency: "USD",
    loan_type: "mortgage",
    principal: "250000",
    interest_rate: "4.5",
    term: { years: 30, months: 0 },
    start_date: "2026-01-01",
    starting_monthly_payment: "1266.71",
    starting_monthly_housing: "0.00",
    starting_total_monthly_payment: "1266.71",
    down_payment: null,
    ltv: null,
    configured_early_payment_fees: { fixed: "0", percent: "0" },
    upfront_fees: "1500",
    total_principal: "250000",
    total_interest: "200000",
    schedule_fees: "0",
    schedule_total_outflow: "450000",
    total_pmi: "0.00",
    total_escrow: "0.00",
    total_cost: "451500",
    payoff_months: 360,
    payoff_month: "2055-12",
    paid_off: true,
    adjustment_counts: { one_time_extra_payments: 0, recurring_extra_payments: 0, interest_rate_changes: 0 },
    cumulative_cost: ["1500.00", "2437.50", "201500.00"],
    horizon: null,
    ...overrides,
  };
}

export function makeComparison(overrides: Partial<PlanComparison> = {}): PlanComparison {
  return {
    directly_comparable: true,
    incomparability_reasons: [],
    overall_winner_plan_ids: [],
    savings_vs_next_best: null,
    best_plan_ids_by_metric: {},
    plans: [makeComparisonItem()],
    horizon_months: null,
    horizon_winner_plan_ids: [],
    ...overrides,
  };
}
