import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, expect, it } from "vitest";
import { PlanSelectionBar } from "./PlanSelectionBar";

describe("PlanSelectionBar", () => {
  it("enables comparison at two selections and reports the four-plan limit", async () => {
    const onCompare = vi.fn();
    const view = render(
      <PlanSelectionBar selectedCount={1} limitReached={false} onCancel={vi.fn()} onCompare={onCompare} />,
    );
    expect(screen.getByRole("button", { name: "Compare" })).toBeDisabled();

    view.rerender(<PlanSelectionBar selectedCount={4} limitReached onCancel={vi.fn()} onCompare={onCompare} />);
    await userEvent.click(screen.getByRole("button", { name: "Compare" }));
    expect(onCompare).toHaveBeenCalledOnce();
    expect(screen.getByText("You can compare up to 4 plans.")).toBeVisible();

    view.rerender(<PlanSelectionBar selectedCount={5} limitReached onCancel={vi.fn()} onCompare={onCompare} />);
    expect(screen.getByRole("button", { name: "Compare" })).toBeDisabled();
  });
});
