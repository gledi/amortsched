import { fromDateValue, toDateValue } from "./date-value";
import type { CreatePlanPayload } from "./plans-api";
import type { InterestRateApplication, LoanType, Plan } from "./types";

export const LOAN_TYPES: ReadonlyArray<{ value: LoanType; label: string }> = [
  { value: "mortgage", label: "Mortgage" },
  { value: "auto", label: "Auto loan" },
  { value: "personal", label: "Personal loan" },
  { value: "student", label: "Student loan" },
  { value: "other", label: "Other" },
];

export const RATE_APPLICATIONS: ReadonlyArray<{ value: InterestRateApplication; label: string }> = [
  { value: "whole_month", label: "Whole month" },
  { value: "prorated_by_days_in_month", label: "Prorated by days in month" },
  { value: "prorated_by_payment_period", label: "Prorated by payment period" },
];

export function loanTypeLabel(value: LoanType): string {
  return LOAN_TYPES.find((option) => option.value === value)?.label ?? "Loan";
}

export interface PlanFormValues {
  name: string;
  loanType: LoanType;
  currency: string;
  lender: string;
  amount: string;
  homePrice: string;
  downPayment: string;
  interestRate: string;
  years: string;
  months: string;
  startDate: string;
  upfrontFees: string;
  earlyFeeFixed: string;
  earlyFeePercent: string;
  application: InterestRateApplication;
  propertyTaxAnnual: string;
  insuranceAnnual: string;
  hoaMonthly: string;
  pmiRate: string;
  pmiCancelLtv: string;
  rateType: "fixed" | "adjustable";
  fixedPeriodYears: string;
  adjustedRate: string;
}

export function defaultPlanFormValues(currency: string, today: Date = new Date()): PlanFormValues {
  return {
    name: "",
    loanType: "mortgage",
    currency,
    lender: "",
    amount: "25000",
    homePrice: "400000",
    downPayment: "80000",
    interestRate: "6.5",
    years: "30",
    months: "0",
    startDate: toDateValue(today),
    upfrontFees: "0",
    earlyFeeFixed: "0",
    earlyFeePercent: "0",
    application: "whole_month",
    propertyTaxAnnual: "0",
    insuranceAnnual: "0",
    hoaMonthly: "0",
    pmiRate: "0",
    pmiCancelLtv: "78",
    rateType: "fixed",
    fixedPeriodYears: "5",
    adjustedRate: "7.5",
  };
}

const text = (value: string | number | null | undefined, fallback = "0") =>
  value === null || value === undefined ? fallback : String(value);

export function planToFormValues(plan: Plan): PlanFormValues {
  const housing = plan.housing_costs;
  const homePrice = housing.property_value;
  return {
    ...defaultPlanFormValues(plan.currency),
    name: plan.name,
    loanType: plan.loan_type,
    currency: plan.currency,
    lender: plan.lender ?? "",
    amount: text(plan.amount),
    homePrice: homePrice === null ? text(plan.amount) : text(homePrice),
    downPayment: homePrice === null ? "0" : text(Number(homePrice) - Number(plan.amount)),
    interestRate: text(plan.interest_rate),
    years: text(plan.term.years),
    months: text(plan.term.months),
    startDate: plan.start_date,
    upfrontFees: text(plan.upfront_fees),
    earlyFeeFixed: text(plan.early_payment_fees.fixed),
    earlyFeePercent: text(plan.early_payment_fees.percent),
    application: plan.interest_rate_application,
    propertyTaxAnnual: text(housing.property_tax_annual),
    insuranceAnnual: text(housing.insurance_annual),
    hoaMonthly: text(housing.hoa_monthly),
    pmiRate: text(housing.pmi_annual_rate),
    pmiCancelLtv: text(housing.pmi_cancel_ltv, "78"),
  };
}

function number(value: string): number {
  return value.trim() === "" ? 0 : Number(value);
}

export function mortgageLoanAmount(values: Pick<PlanFormValues, "homePrice" | "downPayment">): number {
  return number(values.homePrice) - number(values.downPayment);
}

export function addYears(dateValue: string, years: number): string {
  const date = fromDateValue(dateValue) ?? new Date();
  const target = new Date(date.getFullYear() + years, date.getMonth(), date.getDate());
  return toDateValue(target);
}

export type ParsedPlanForm = { payload: CreatePlanPayload } | { error: string };

export function parsePlanForm(values: PlanFormValues, options: { allowAdjustableRate: boolean }): ParsedPlanForm {
  const name = values.name.trim();
  if (!name) return { error: "Plan name is required" };

  const isMortgage = values.loanType === "mortgage";
  const homePrice = number(values.homePrice);
  const downPayment = number(values.downPayment);
  const amount = isMortgage ? homePrice - downPayment : number(values.amount);
  if (isMortgage) {
    if (!Number.isFinite(homePrice) || homePrice <= 0) return { error: "Enter the home price" };
    if (!Number.isFinite(downPayment) || downPayment < 0) return { error: "Down payment must be zero or greater" };
    if (downPayment >= homePrice) return { error: "Down payment must be less than the home price" };
  } else if (!Number.isFinite(amount) || amount <= 0) {
    return { error: "Enter a loan amount greater than 0" };
  }

  const rate = number(values.interestRate);
  if (!Number.isFinite(rate) || rate < 0 || rate > 100) return { error: "Interest rate must be between 0% and 100%" };

  const years = Math.trunc(number(values.years));
  const months = Math.trunc(number(values.months));
  if (years < 0 || years > 50 || months < 0 || months > 11) return { error: "Enter a term of up to 50 years" };
  if (years === 0 && months === 0) return { error: "Term must be at least one month" };

  const nonNegative: Array<[string, string]> = [
    [values.upfrontFees, "Upfront fees"],
    [values.earlyFeeFixed, "Early payoff fee"],
    [values.earlyFeePercent, "Early payoff fee percent"],
  ];
  if (isMortgage) {
    nonNegative.push(
      [values.propertyTaxAnnual, "Property tax"],
      [values.insuranceAnnual, "Insurance"],
      [values.hoaMonthly, "HOA dues"],
      [values.pmiRate, "PMI rate"],
    );
  }
  for (const [raw, label] of nonNegative) {
    const parsed = number(raw);
    if (!Number.isFinite(parsed) || parsed < 0) return { error: `${label} must be zero or greater` };
  }
  if (number(values.earlyFeePercent) > 100) return { error: "Early payoff fee percent must be at most 100%" };
  const pmiCancelLtv = number(values.pmiCancelLtv);
  if (isMortgage && (pmiCancelLtv <= 0 || pmiCancelLtv > 100)) return { error: "PMI cancellation LTV must be 1-100%" };

  const payload: CreatePlanPayload = {
    name,
    loan_type: values.loanType,
    currency: values.currency,
    amount,
    interest_rate: rate,
    term: { years, months },
    start_date: values.startDate || undefined,
    lender: values.lender.trim(),
    upfront_fees: number(values.upfrontFees),
    early_payment_fees: { fixed: number(values.earlyFeeFixed), percent: number(values.earlyFeePercent) },
    housing_costs: isMortgage
      ? {
          property_value: homePrice,
          property_tax_annual: number(values.propertyTaxAnnual),
          insurance_annual: number(values.insuranceAnnual),
          hoa_monthly: number(values.hoaMonthly),
          pmi_annual_rate: number(values.pmiRate),
          pmi_cancel_ltv: pmiCancelLtv,
        }
      : {},
    interest_rate_application: values.application,
  };

  if (options.allowAdjustableRate && values.rateType === "adjustable") {
    const fixedYears = Math.trunc(number(values.fixedPeriodYears));
    const adjusted = number(values.adjustedRate);
    if (fixedYears < 1 || fixedYears * 12 >= years * 12 + months) {
      return { error: "The fixed-rate period must be at least a year and shorter than the term" };
    }
    if (!Number.isFinite(adjusted) || adjusted < 0 || adjusted > 100) {
      return { error: "Rate after the fixed period must be between 0% and 100%" };
    }
    payload.interest_rate_changes = [
      { effective_date: addYears(values.startDate || toDateValue(new Date()), fixedYears), rate: adjusted },
    ];
  }

  return { payload };
}
