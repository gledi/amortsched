export type InterestRateApplication = "whole_month" | "prorated_by_days_in_month" | "prorated_by_payment_period";
export type PlanStatus = "draft" | "saved";
export type LoanType = "mortgage" | "auto" | "personal" | "student" | "other";
type Money = string | number;

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

export interface HousingCosts {
  property_value: Money | null;
  property_tax_annual: Money;
  insurance_annual: Money;
  hoa_monthly: Money;
  pmi_annual_rate: Money;
  pmi_cancel_ltv: Money;
}

export interface HousingPayment {
  property_tax: Money;
  insurance: Money;
  hoa: Money;
  pmi: Money;
  total: Money;
}

export interface Adjustments {
  one_time_extra_payments: ExtraPayment[];
  recurring_extra_payments: RecurringExtraPayment[];
  interest_rate_changes: InterestRateChange[];
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
  loan_type: LoanType;
  currency: string;
  lender?: string | null;
  upfront_fees?: string | number;
  early_payment_fees: EarlyPaymentFees;
  housing_costs: HousingCosts;
  down_payment: Money | null;
  ltv: Money | null;
  monthly_payment: Money;
  monthly_housing: HousingPayment | null;
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

export interface HorizonCost {
  months: number;
  cost: Money;
  balance: Money;
  payoff_penalty: Money;
}

export interface PlanComparisonItem {
  id: string;
  name: string;
  lender: string | null;
  currency: string;
  loan_type: LoanType;
  principal: string | number;
  interest_rate: string | number;
  term: Term;
  start_date: string;
  starting_monthly_payment: string | number;
  starting_monthly_housing: Money;
  starting_total_monthly_payment: Money;
  down_payment: Money | null;
  ltv: Money | null;
  configured_early_payment_fees: EarlyPaymentFees;
  upfront_fees: string | number;
  total_principal: string | number;
  total_interest: string | number;
  schedule_fees: string | number;
  schedule_total_outflow: string | number;
  total_pmi: Money;
  total_escrow: Money;
  total_cost: string | number;
  payoff_months: number;
  payoff_month: string;
  paid_off: boolean;
  adjustment_counts: AdjustmentCounts;
  cumulative_cost: Money[];
  horizon: HorizonCost | null;
}

export type BestPlanIdsByMetric = Record<string, string[]>;

export interface PlanComparison {
  directly_comparable: boolean;
  incomparability_reasons: string[];
  overall_winner_plan_ids: string[];
  savings_vs_next_best: string | number | null;
  best_plan_ids_by_metric: BestPlanIdsByMetric;
  plans: PlanComparisonItem[];
  horizon_months: number | null;
  horizon_winner_plan_ids: string[];
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
  housing: HousingPayment | null;
  total_with_housing: Money;
}

export interface Totals {
  principal: string | number;
  interest: string | number;
  fees: string | number;
  total_outflow: string | number;
  months: number;
  paid_off: boolean;
  pmi: Money;
  escrow: Money;
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
  email_verified: boolean;
}

export interface Profile {
  id: string;
  user_id: string;
  display_name: string | null;
  phone: string | null;
  locale: string | null;
  timezone: string | null;
  currency: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdate {
  display_name?: string | null;
  phone?: string | null;
  locale?: string | null;
  timezone?: string | null;
  currency?: string | null;
}
