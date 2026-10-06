import * as React from "react";
import { useState } from "react";
import { PlusIcon } from "lucide-react";
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
import { useDefaultCurrency } from "@/hooks/use-default-currency";
import { defaultPlanFormValues, parsePlanForm, type PlanFormValues } from "@/lib/plan-form";
import { plansApi } from "@/lib/plans-api";
import type { Plan } from "@/lib/types";

interface CreatePlanDialogProps {
  onPlanCreated: (plan: Plan) => void;
  trigger?: React.ReactElement;
  initialValues?: Partial<PlanFormValues>;
}

export function CreatePlanDialog({ onPlanCreated, trigger, initialValues }: CreatePlanDialogProps) {
  const defaultCurrency = useDefaultCurrency();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initial = () => ({ ...defaultPlanFormValues(defaultCurrency), ...initialValues });
  const [values, setValues] = useState<PlanFormValues>(initial);

  function handleOpenChange(next: boolean) {
    if (next) {
      setValues(initial());
      setError(null);
    }
    setOpen(next);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const parsed = parsePlanForm(values, { allowAdjustableRate: true });
    if ("error" in parsed) {
      setError(parsed.error);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const plan = await plansApi.createPlan(parsed.payload);
      setOpen(false);
      onPlanCreated(plan);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create plan");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          trigger ?? (
            <Button>
              <PlusIcon data-icon="inline-start" />
              New plan
            </Button>
          )
        }
      />
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>New loan plan</DialogTitle>
          <DialogDescription>
            Enter an offer you received or a loan you&apos;re considering. You can add extra payments later.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error ? (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
          <PlanFormFields
            idPrefix="create-plan"
            values={values}
            onChange={(patch) => setValues((current) => ({ ...current, ...patch }))}
            allowAdjustableRate
          />
          <DialogFooter className="mt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? <Spinner data-icon="inline-start" /> : null}
              {loading ? "Creating..." : "Create plan"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
