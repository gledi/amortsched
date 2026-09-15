import { describe, expect, it } from "vitest";
import { fromDateValue, toDateValue } from "./date-value";

describe("date values", () => {
  it("parses an ISO date as a local calendar date", () => {
    const date = fromDateValue("2026-09-15");

    expect(date).toEqual(new Date(2026, 8, 15));
  });

  it("formats a local calendar date without a UTC shift", () => {
    const date = new Date(2026, 8, 15, 23, 30);

    expect(toDateValue(date)).toBe("2026-09-15");
  });

  it("treats empty and invalid values as unselected", () => {
    expect(fromDateValue("")).toBeUndefined();
    expect(fromDateValue("not-a-date")).toBeUndefined();
    expect(toDateValue(undefined)).toBe("");
  });
});
