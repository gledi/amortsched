import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { plansApi } from "@/lib/plans-api";
import type { Plan } from "@/lib/types";
import { EditPlanDialog } from "./EditPlanDialog";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("submits an explicit blank lender when clearing an existing lender", async () => {
  const plan: Plan = {
    id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    user_id: "owner",
    name: "Offer",
    slug: "offer",
    amount: "1200",
    interest_rate: "3",
    term: { years: 1, months: 0 },
    start_date: "2026-01-01",
    lender: "Bank Alpha",
    upfront_fees: "0",
    early_payment_fees: { fixed: "0", percent: "0" },
    interest_rate_application: "whole_month",
    status: "draft",
    one_time_extra_payments: [],
    recurring_extra_payments: [],
    interest_rate_changes: [],
    created_at: "2026-01-01",
    updated_at: "2026-01-01",
  };
  const updated = { ...plan, lender: null };
  const update = vi.spyOn(plansApi, "updatePlan").mockResolvedValue(updated);
  const onPlanUpdated = vi.fn();
  render(<EditPlanDialog plan={plan} onPlanUpdated={onPlanUpdated} />);
  await userEvent.click(screen.getByRole("button", { name: "Edit" }));
  await userEvent.clear(screen.getByRole("textbox", { name: "Lender" }));
  await userEvent.click(screen.getByRole("button", { name: "Save Changes" }));
  await waitFor(() => expect(update).toHaveBeenCalledWith(plan.id, expect.objectContaining({ lender: "" })));
  expect(onPlanUpdated).toHaveBeenCalledWith(updated);
});
