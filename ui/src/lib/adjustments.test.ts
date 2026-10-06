import { describe, expect, it } from "vitest";
import { parseAdjustment, removeAdjustment, toFormValues, upsertAdjustment } from "./adjustments";
import type { Adjustments } from "./types";

const empty: Adjustments = { one_time_extra_payments: [], recurring_extra_payments: [], interest_rate_changes: [] };

describe("adjustment list edits", () => {
  it("adds, replaces, and removes items without touching other lists", () => {
    const added = upsertAdjustment(empty, "one_time", { date: "2027-01-01", amount: 100 });
    const second = upsertAdjustment(added, "one_time", { date: "2028-01-01", amount: 200 });
    const edited = upsertAdjustment(second, "one_time", { date: "2027-06-01", amount: 150 }, 0);
    expect(edited.one_time_extra_payments).toEqual([
      { date: "2027-06-01", amount: 150 },
      { date: "2028-01-01", amount: 200 },
    ]);
    expect(removeAdjustment(edited, "one_time", 0).one_time_extra_payments).toEqual([
      { date: "2028-01-01", amount: 200 },
    ]);
    expect(edited.interest_rate_changes).toBe(empty.interest_rate_changes);
  });
});

describe("parseAdjustment", () => {
  it("parses each kind", () => {
    expect(parseAdjustment("one_time", { date: "2027-01-01", amount: "500", count: "", rate: "" })).toEqual({
      value: { date: "2027-01-01", amount: 500 },
    });
    expect(parseAdjustment("recurring", { date: "2027-01-01", amount: "50", count: "24", rate: "" })).toEqual({
      value: { start_date: "2027-01-01", amount: 50, count: 24 },
    });
    expect(parseAdjustment("rate_change", { date: "2030-01-01", amount: "", count: "", rate: "0" })).toEqual({
      value: { effective_date: "2030-01-01", rate: 0 },
    });
  });

  it("rejects invalid values", () => {
    expect(parseAdjustment("one_time", { date: "2027-01-01", amount: "0", count: "", rate: "" })).toEqual({
      error: "Amount must be greater than 0",
    });
    expect(parseAdjustment("recurring", { date: "2027-01-01", amount: "5", count: "1.5", rate: "" })).toEqual({
      error: "Number of payments must be 1 to 600",
    });
    expect(parseAdjustment("rate_change", { date: "", amount: "", count: "", rate: "5" })).toEqual({
      error: "Choose a date",
    });
  });

  it("prefills the form from an existing value", () => {
    expect(toFormValues("recurring", { start_date: "2027-02-01", amount: "75", count: 6 }, "2026-01-01")).toMatchObject(
      { date: "2027-02-01", amount: "75", count: "6" },
    );
  });
});
