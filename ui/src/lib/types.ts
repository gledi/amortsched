export type InterestRateApplication = "whole_month" | "prorated_days" | "prorated_payment_period";
export type PlanStatus = "draft" | "saved";

export interface Term {
  years: number;
  months: number;
}

export interface EarlyPaymentFees {
  fixed: string | number;
  percent: string | number;
}

export interface ExtraPayment {
  date: string;
  amount: string | number;
}

export interface RecurringExtraPayment {
  start_date: string;
  amount: string | number;
  count: number;
}

export interface InterestRateChange {
  effective_date: string;
  rate: string | number;
}

export interface Plan {
  id: string;
  user_id: string;
  name: string;
  slug: string;
  amount: string | number;
  interest_rate: string | number;
  term: Term;
  start_date: string;
  lender?: string | null;
  upfront_fees?: string | number;
  early_payment_fees: EarlyPaymentFees;
  interest_rate_application: InterestRateApplication;
  status: PlanStatus;
  one_time_extra_payments: ExtraPayment[];
  recurring_extra_payments: RecurringExtraPayment[];
  interest_rate_changes: InterestRateChange[];
  created_at: string;
  updated_at: string;
}

export interface AdjustmentCounts {
  one_time_extra_payments: number;
  recurring_extra_payments: number;
  interest_rate_changes: number;
}

export interface PlanComparisonItem {
  id: string;
  name: string;
  lender: string | null;
  principal: string | number;
  interest_rate: string | number;
  term: Term;
  start_date: string;
  starting_monthly_payment: string | number;
  configured_early_payment_fees: EarlyPaymentFees;
  upfront_fees: string | number;
  total_principal: string | number;
  total_interest: string | number;
  schedule_fees: string | number;
  schedule_total_outflow: string | number;
  total_cost: string | number;
  payoff_months: number;
  payoff_month: string;
  paid_off: boolean;
  adjustment_counts: AdjustmentCounts;
}

export type BestPlanIdsByMetric = Record<string, string[]>;

export interface PlanComparison {
  directly_comparable: boolean;
  incomparability_reasons: string[];
  overall_winner_plan_ids: string[];
  savings_vs_next_best: string | number | null;
  best_plan_ids_by_metric: BestPlanIdsByMetric;
  plans: PlanComparisonItem[];
}

export interface Balance {
  before: string | number;
  after: string | number;
}

export interface Installment {
  installment_number: number | null;
  year: number;
  month: number;
  month_name: string;
  type: string;
  principal: string | number;
  interest: string | number;
  fees: string | number;
  total: string | number;
  balance: Balance;
}

export interface Totals {
  principal: string | number;
  interest: string | number;
  fees: string | number;
  total_outflow: string | number;
  months: number;
  paid_off: boolean;
}

export interface Schedule {
  id: string;
  plan_id: string;
  installments: Installment[];
  totals: Totals | null;
  generated_at: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
}
