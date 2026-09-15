import * as React from "react";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { DatePicker } from "@/components/ui/date-picker";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { toDateValue } from "@/lib/date-value";
import { plansApi } from "@/lib/plans-api";
import { TrendingUpIcon } from "lucide-react";
import type { Plan } from "@/lib/types";

interface AddInterestRateChangeDialogProps {
  planId: string;
  defaultDate?: string;
  onRateChangeAdded: (updatedPlan: Plan) => void;
  trigger?: React.ReactElement;
}

export function AddInterestRateChangeDialog({
  planId,
  defaultDate,
  onRateChangeAdded,
  trigger,
}: AddInterestRateChangeDialogProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [effectiveDate, setEffectiveDate] = useState(defaultDate || toDateValue(new Date()));
  const [rate, setRate] = useState("5.0");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const numRate = parseFloat(rate);
    if (isNaN(numRate) || numRate < 0 || numRate > 100) {
      setError("Please enter a valid interest rate between 0% and 100%");
      return;
    }
    if (!effectiveDate) {
      setError("Please select an effective date");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const updatedPlan = await plansApi.addInterestRateChange(planId, {
        effective_date: effectiveDate,
        rate: numRate,
      });
      setOpen(false);
      onRateChangeAdded(updatedPlan);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add interest rate change");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          trigger ?? (
            <Button size="sm" variant="outline">
              <TrendingUpIcon data-icon="inline-start" />
              Add Interest Rate Change
            </Button>
          )
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Interest Rate Change</DialogTitle>
          <DialogDescription>
            Adjust the annual interest rate starting from a specific effective date.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="rate-effective-date">Effective Date</FieldLabel>
              <DatePicker id="rate-effective-date" value={effectiveDate} onValueChange={setEffectiveDate} required />
            </Field>

            <Field>
              <FieldLabel htmlFor="rate-new-rate">New Annual Interest Rate (%)</FieldLabel>
              <Input
                id="rate-new-rate"
                type="number"
                step="0.01"
                min="0"
                max="100"
                placeholder="5.0"
                value={rate}
                onChange={(e) => setRate(e.target.value)}
                required
              />
            </Field>
          </FieldGroup>

          <DialogFooter className="mt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading && <Spinner data-icon="inline-start" />}
              {loading ? "Adding..." : "Add Rate Change"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
