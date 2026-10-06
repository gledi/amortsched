import { describe, expect, it } from "vitest";
import { addYears, defaultPlanFormValues, parsePlanForm, planToFormValues } from "./plan-form";
import type { Plan } from "./types";

const base = { ...defaultPlanFormValues("EUR", new Date(2026, 0, 15)), name: "  Home  " };

function payloadOf(result: ReturnType<typeof parsePlanForm>) {
  if ("error" in result) throw new Error(result.error);
  return result.payload;
}

describe("parsePlanForm", () => {
  it("derives the mortgage loan amount from price and down payment", () => {
    const payload = payloadOf(
      parsePlanForm(
        { ...base, propertyTaxAnnual: "4800", insuranceAnnual: "1200", pmiRate: "0.5" },
        { allowAdjustableRate: false },
      ),
    );
    expect(payload.name).toBe("Home");
    expect(payload.currency).toBe("EUR");
    expect(payload.amount).toBe(320000);
    expect(payload.housing_costs).toEqual({
      property_value: 400000,
      property_tax_annual: 4800,
      insurance_annual: 1200,
      hoa_monthly: 0,
      pmi_annual_rate: 0.5,
      pmi_cancel_ltv: 78,
    });
    expect(payload.interest_rate_changes).toBeUndefined();
  });

  it("sends no housing costs for non-mortgage loans", () => {
    const payload = payloadOf(
      parsePlanForm({ ...base, loanType: "auto", amount: "30000" }, { allowAdjustableRate: false }),
    );
    expect(payload.amount).toBe(30000);
    expect(payload.housing_costs).toEqual({});
  });

  it("turns an adjustable-rate preset into a dated rate change", () => {
    const payload = payloadOf(
      parsePlanForm(
        { ...base, rateType: "adjustable", fixedPeriodYears: "5", adjustedRate: "7.25" },
        { allowAdjustableRate: true },
      ),
    );
    expect(payload.interest_rate_changes).toEqual([{ effective_date: "2031-01-15", rate: 7.25 }]);
  });

  it("ignores the adjustable preset when editing", () => {
    const payload = payloadOf(parsePlanForm({ ...base, rateType: "adjustable" }, { allowAdjustableRate: false }));
    expect(payload.interest_rate_changes).toBeUndefined();
  });

  it.each([
    [{ name: " " }, "Plan name is required"],
    [{ downPayment: "400000" }, "Down payment must be less than the home price"],
    [{ interestRate: "101" }, "Interest rate must be between 0% and 100%"],
    [{ years: "0", months: "0" }, "Term must be at least one month"],
    [{ pmiRate: "-1" }, "PMI rate must be zero or greater"],
    [
      { rateType: "adjustable" as const, fixedPeriodYears: "30" },
      "The fixed-rate period must be at least a year and shorter than the term",
    ],
  ])("rejects %o", (overrides, error) => {
    expect(parsePlanForm({ ...base, ...overrides }, { allowAdjustableRate: true })).toEqual({ error });
  });
});

describe("planToFormValues", () => {
  it("round-trips a mortgage through the form", () => {
    const plan = {
      name: "Home",
      loan_type: "mortgage",
      currency: "GBP",
      lender: null,
      amount: "320000.00",
      interest_rate: "6.5",
      term: { years: 30, months: 0 },
      start_date: "2026-01-01",
      upfront_fees: "1000",
      early_payment_fees: { fixed: "0", percent: "1" },
      interest_rate_application: "whole_month",
      housing_costs: {
        property_value: "400000",
        property_tax_annual: "4800",
        insurance_annual: "1200",
        hoa_monthly: "0",
        pmi_annual_rate: "0",
        pmi_cancel_ltv: "78",
      },
    } as unknown as Plan;
    const values = planToFormValues(plan);
    expect(values.homePrice).toBe("400000");
    expect(values.downPayment).toBe("80000");
    const payload = payloadOf(parsePlanForm(values, { allowAdjustableRate: false }));
    expect(payload.amount).toBe(320000);
    expect(payload.lender).toBe("");
  });
});

describe("addYears", () => {
  it("keeps the calendar day", () => {
    expect(addYears("2026-03-31", 2)).toBe("2028-03-31");
  });
});
