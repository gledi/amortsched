import { describe, expect, it } from "vitest";
import { problemMessage } from "./api-client";
import { safeRedirectTarget } from "./auth";

describe("problemMessage", () => {
  it("uses problem detail strings", () => {
    expect(problemMessage(400, { detail: "This link is invalid or has expired" })).toBe(
      "This link is invalid or has expired",
    );
  });

  it("flattens FastAPI validation errors", () => {
    const body = { detail: [{ loc: ["body", "password"], msg: "String should have at least 8 characters" }] };
    expect(problemMessage(422, body)).toBe("password: String should have at least 8 characters");
  });

  it("prefers domain validation errors", () => {
    expect(problemMessage(422, { detail: "Validation failed", errors: [{ message: "Bad currency" }] })).toBe(
      "Bad currency",
    );
  });

  it("explains rate limiting", () => {
    expect(problemMessage(429, { detail: "Too many attempts" })).toMatch(/wait/);
  });
});

describe("safeRedirectTarget", () => {
  it("keeps same-origin paths", () => {
    expect(safeRedirectTarget("/plans/1?x=2")).toBe("/plans/1?x=2");
  });

  it("rejects external and protocol-relative targets", () => {
    expect(safeRedirectTarget("https://evil.example")).toBe("/");
    expect(safeRedirectTarget("//evil.example")).toBe("/");
    expect(safeRedirectTarget("/\\evil.example")).toBe("/");
    expect(safeRedirectTarget("/\t/evil.example")).toBe("/");
    expect(safeRedirectTarget(undefined)).toBe("/");
  });
});
