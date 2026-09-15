import { describe, expect, it } from "vitest";
import { parsePlanOfferFields } from "./plan-offer-values";

describe("parsePlanOfferFields", () => {
  it("normalizes an optional lender and non-negative upfront fees", () => {
    expect(parsePlanOfferFields("  Bank Alpha  ", "1250.50")).toEqual({
      lender: "Bank Alpha",
      upfront_fees: 1250.5,
    });
    expect(parsePlanOfferFields("   ", "")).toEqual({ lender: null, upfront_fees: 0 });
  });

  it("rejects invalid upfront fees", () => {
    expect(parsePlanOfferFields("Bank", "-1")).toEqual({ error: "Upfront fees must be zero or greater" });
    expect(parsePlanOfferFields("Bank", "not-a-number")).toEqual({ error: "Enter valid upfront fees" });
  });
});
