import type { Adjustments, ExtraPayment, InterestRateChange, Plan, RecurringExtraPayment } from "./types";

export type AdjustmentKind = "one_time" | "recurring" | "rate_change";

export interface AdjustmentFormValues {
  date: string;
  amount: string;
  count: string;
  rate: string;
}

export type AdjustmentValue = ExtraPayment | RecurringExtraPayment | InterestRateChange;

export function adjustmentsOf(plan: Plan): Adjustments {
  return {
    one_time_extra_payments: plan.one_time_extra_payments ?? [],
    recurring_extra_payments: plan.recurring_extra_payments ?? [],
    interest_rate_changes: plan.interest_rate_changes ?? [],
  };
}

const LIST_KEY = {
  one_time: "one_time_extra_payments",
  recurring: "recurring_extra_payments",
  rate_change: "interest_rate_changes",
} as const satisfies Record<AdjustmentKind, keyof Adjustments>;

export function upsertAdjustment(
  current: Adjustments,
  kind: AdjustmentKind,
  value: AdjustmentValue,
  index?: number,
): Adjustments {
  const key = LIST_KEY[kind];
  const list = [...(current[key] as AdjustmentValue[])];
  if (index === undefined) list.push(value);
  else list[index] = value;
  return { ...current, [key]: list };
}

export function removeAdjustment(current: Adjustments, kind: AdjustmentKind, index: number): Adjustments {
  const key = LIST_KEY[kind];
  return { ...current, [key]: (current[key] as AdjustmentValue[]).filter((_, position) => position !== index) };
}

export function toFormValues(kind: AdjustmentKind, value: AdjustmentValue | undefined, defaultDate: string) {
  const values: AdjustmentFormValues = { date: defaultDate, amount: "1000", count: "12", rate: "5" };
  if (!value) {
    if (kind === "recurring") values.amount = "200";
    return values;
  }
  if (kind === "one_time") {
    const payment = value as ExtraPayment;
    return { ...values, date: payment.date, amount: String(payment.amount) };
  }
  if (kind === "recurring") {
    const payment = value as RecurringExtraPayment;
    return { ...values, date: payment.start_date, amount: String(payment.amount), count: String(payment.count) };
  }
  const change = value as InterestRateChange;
  return { ...values, date: change.effective_date, rate: String(change.rate) };
}

export function parseAdjustment(
  kind: AdjustmentKind,
  values: AdjustmentFormValues,
): { value: AdjustmentValue } | { error: string } {
  if (!values.date) return { error: "Choose a date" };
  if (kind === "rate_change") {
    const rate = Number(values.rate);
    if (values.rate.trim() === "" || !Number.isFinite(rate) || rate < 0 || rate > 100) {
      return { error: "Rate must be between 0% and 100%" };
    }
    return { value: { effective_date: values.date, rate } };
  }
  const amount = Number(values.amount);
  if (!Number.isFinite(amount) || amount <= 0) return { error: "Amount must be greater than 0" };
  if (kind === "one_time") return { value: { date: values.date, amount } };
  const count = Number(values.count);
  if (!Number.isInteger(count) || count < 1 || count > 600) return { error: "Number of payments must be 1 to 600" };
  return { value: { start_date: values.date, amount, count } };
}
