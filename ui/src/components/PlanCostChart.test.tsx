import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { PlanComparisonItem } from "@/lib/types";
import { makeComparison, makeComparisonItem } from "@/test/fixtures";
import { PlanCostChart } from "./PlanCostChart";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("distinguishes offers from the same lender on the cost chart", async () => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
    return this.classList.contains("recharts-responsive-container")
      ? new DOMRect(0, 0, 960, 320)
      : new DOMRect(0, 0, (this.textContent?.length ?? 0) * 7, 16);
  });
  const plan: PlanComparisonItem = makeComparisonItem({ id: "first", name: "Fixed offer", lender: "Shared Bank" });
  render(
    <PlanCostChart
      comparison={makeComparison({ plans: [plan, { ...plan, id: "second", name: "Flexible offer" }] })}
      currency="USD"
    />,
  );
  expect(await screen.findByText("Shared Bank — Fixed offer")).toBeInTheDocument();
  expect(screen.getByText("Shared Bank — Flexible offer")).toBeInTheDocument();
});
