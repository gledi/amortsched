import { describe, expect, it } from "vitest";
import { isComparableSelection, parsePlanIds, togglePlanSelection } from "./plan-selection";

describe("plan comparison selection", () => {
  it("parses ordered unique IDs from the URL", () => {
    expect(parsePlanIds("a,b,c")).toEqual(["a", "b", "c"]);
    expect(parsePlanIds(" a, b, a, ,c ")).toEqual(["a", "b", "c"]);
  });

  it("requires two plans and caps selection at four", () => {
    expect(isComparableSelection(["a"])).toBe(false);
    expect(isComparableSelection(["a", "b"])).toBe(true);
    expect(isComparableSelection(["a", "b", "c", "d", "e"])).toBe(false);
    expect(togglePlanSelection(["a", "b", "c", "d"], "e")).toEqual({
      ids: ["a", "b", "c", "d"],
      limitReached: true,
    });
  });

  it("normalizes UUID casing before deduplicating restored selections", () => {
    const id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
    expect(parsePlanIds(`${id.toUpperCase()},${id}`)).toEqual([id]);
  });

  it("toggles an existing selection off", () => {
    expect(togglePlanSelection(["a", "b", "c"], "b")).toEqual({
      ids: ["a", "c"],
      limitReached: false,
    });
  });
});
