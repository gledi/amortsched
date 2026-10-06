import { api } from "./api-client";

type Money = string | number;

export interface AffordabilityRequest {
  gross_monthly_income: number;
  monthly_debts: number;
  down_payment: number;
  interest_rate: number;
  term_months: number;
  property_tax_rate: number;
  insurance_annual: number;
  hoa_monthly: number;
  pmi_annual_rate: number;
  front_end_ratio: number;
  back_end_ratio: number;
}

export interface AffordabilityResult {
  max_home_price: Money;
  max_loan_amount: Money;
  max_monthly_housing: Money;
  limiting_ratio: "front_end" | "back_end";
  monthly: {
    principal_interest: Money;
    property_tax: Money;
    insurance: Money;
    hoa: Money;
    pmi: Money;
    total: Money;
  };
  front_end_ratio: Money;
  back_end_ratio: Money;
  ltv: Money | null;
  down_payment_percent: Money | null;
}

export interface RefinanceRequest {
  plan_id?: string;
  as_of?: string;
  current_balance?: number;
  current_rate?: number;
  remaining_months?: number;
  new_rate: number;
  new_term_months: number;
  closing_costs: number;
  roll_costs_into_loan: boolean;
}

export interface RefinanceResult {
  current_loan: { balance: Money; rate: Money; remaining_months: number; currency: string | null };
  current_payment: Money;
  new_payment: Money;
  monthly_savings: Money;
  new_principal: Money;
  cash_due_at_closing: Money;
  current_total_interest: Money;
  new_total_interest: Money;
  current_total_paid: Money;
  new_total_paid: Money;
  lifetime_savings: Money;
  break_even_month: number | null;
  advantage_by_month: Money[];
}

export interface PrepayVsInvestRequest {
  plan_id?: string;
  principal?: number;
  interest_rate?: number;
  term_months?: number;
  extra_monthly: number;
  annual_return: number;
}

export interface PrepayVsInvestResult {
  loan: { principal: Money; interest_rate: Money; term_months: number; currency: string | null };
  regular_payment: Money;
  payoff_months_with_prepayment: number;
  months_saved: number;
  interest_without_prepayment: Money;
  interest_with_prepayment: Money;
  interest_saved: Money;
  prepay_net_worth: Money;
  invest_net_worth: Money;
  advantage: Money;
  better_strategy: "prepay" | "invest" | "tie";
  break_even_return: Money | null;
  timeline: { month: number; prepay: Money; invest: Money }[];
}

export const toolsApi = {
  affordability: (body: AffordabilityRequest) =>
    api<AffordabilityResult>("/tools/affordability", { method: "POST", body }),
  refinance: (body: RefinanceRequest) => api<RefinanceResult>("/tools/refinance", { method: "POST", body }),
  prepayVsInvest: (body: PrepayVsInvestRequest) =>
    api<PrepayVsInvestResult>("/tools/prepay-vs-invest", { method: "POST", body }),
};
