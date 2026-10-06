import type { ReactNode } from "react";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { plansApi } from "@/lib/plans-api";
import type { Plan } from "@/lib/types";
import { makePlan } from "@/test/fixtures";
import { DashboardPage, principalByCurrency } from "./DashboardPage";

const location = vi.hoisted(() => ({ compare: "", navigate: vi.fn() }));
vi.mock("@tanstack/react-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-router")>();
  return {
    ...actual,
    useRouter: () => ({ navigate: location.navigate }),
    getRouteApi: () => ({ useSearch: () => ({ compare: location.compare }) }),
    Link: ({ children }: { children: ReactNode }) => <a>{children}</a>,
  };
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const ids = ["aaaaaaaa", "bbbbbbbb", "cccccccc", "dddddddd", "eeeeeeee"].map(
  (prefix) => `${prefix}-aaaa-aaaa-aaaa-aaaaaaaaaaaa`,
);
const plans: Plan[] = ids.map((id, index) =>
  makePlan({ id, name: `Offer ${index + 1}`, slug: `offer-${index + 1}`, lender: "Bank Alpha" }),
);

it.each([
  ["malformed", `${ids[0]},bad-id`, 1],
  ["missing", `${ids[0]},ffffffff-aaaa-aaaa-aaaa-aaaaaaaaaaaa`, 1],
  ["uppercase", `${ids[0].toUpperCase()},${ids[1]}`, 2],
  ["five IDs", ids.join(","), 4],
])("reconciles restored %s selection with loaded plans", async (_case, compare, count) => {
  location.compare = String(compare);
  location.navigate.mockClear();
  vi.spyOn(plansApi, "listPlans").mockResolvedValue(plans);
  await act(async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DashboardPage />
      </QueryClientProvider>,
    );
  });
  await waitFor(() => expect(screen.getAllByRole("checkbox", { checked: true })).toHaveLength(Number(count)));
  expect(screen.getByText(`${count} ${count === 1 ? "plan" : "plans"} selected`)).toBeVisible();
  const compareButton = screen.getByRole("button", { name: "Compare" });
  if (Number(count) < 2) {
    expect(compareButton).toBeDisabled();
  } else {
    await userEvent.click(compareButton);
    expect(location.navigate).toHaveBeenCalledWith({
      to: "/compare",
      search: { plans: ids.slice(0, Number(count)).join(",") },
    });
  }
  if (_case !== "uppercase") expect(screen.getByRole("alert")).toHaveTextContent(/removed/i);
  expect(screen.getAllByText("Bank Alpha")).toHaveLength(5);
  expect(screen.getByText("Offer 1")).toBeVisible();
});

it("totals principal per currency", () => {
  expect(
    principalByCurrency([
      makePlan({ amount: "1000", currency: "USD" }),
      makePlan({ amount: "500", currency: "USD" }),
      makePlan({ amount: "200", currency: "EUR" }),
    ]),
  ).toBe("$1,500.00 · €200.00");
});
