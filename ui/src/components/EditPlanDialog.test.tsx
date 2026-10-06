import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { plansApi } from "@/lib/plans-api";
import type { Plan } from "@/lib/types";
import { makePlan } from "@/test/fixtures";
import { EditPlanDialog } from "./EditPlanDialog";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("submits an explicit blank lender when clearing an existing lender", async () => {
  const plan: Plan = makePlan({ lender: "Bank Alpha" });
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
