import * as React from "react";
import { useState } from "react";
import { Edit3Icon } from "lucide-react";
import { PlanFormFields } from "@/components/PlanFormFields";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { parsePlanForm, planToFormValues, type PlanFormValues } from "@/lib/plan-form";
import { plansApi } from "@/lib/plans-api";
import type { Plan } from "@/lib/types";

interface EditPlanDialogProps {
  plan: Plan;
  onPlanUpdated: (plan: Plan) => void;
  trigger?: React.ReactElement;
}

export function EditPlanDialog({ plan, onPlanUpdated, trigger }: EditPlanDialogProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState<PlanFormValues>(() => planToFormValues(plan));

  function handleOpenChange(next: boolean) {
    if (next) {
      setValues(planToFormValues(plan));
      setError(null);
    }
    setOpen(next);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const parsed = parsePlanForm(values, { allowAdjustableRate: false });
    if ("error" in parsed) {
      setError(parsed.error);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const updated = await plansApi.updatePlan(plan.id, parsed.payload);
      setOpen(false);
      onPlanUpdated(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update plan");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          trigger ?? (
            <Button variant="outline" size="sm">
              <Edit3Icon data-icon="inline-start" />
              Edit
            </Button>
          )
        }
      />
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit plan</DialogTitle>
          <DialogDescription>Change the loan terms. Regenerate the schedule to see the effect.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error ? (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
          <PlanFormFields
            idPrefix="edit-plan"
            values={values}
            onChange={(patch) => setValues((current) => ({ ...current, ...patch }))}
            allowAdjustableRate={false}
          />
          <DialogFooter className="mt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? <Spinner data-icon="inline-start" /> : null}
              {loading ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
