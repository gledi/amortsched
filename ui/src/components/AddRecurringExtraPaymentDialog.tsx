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
import { RepeatIcon } from "lucide-react";
import type { Plan } from "@/lib/types";

interface AddRecurringExtraPaymentDialogProps {
  planId: string;
  defaultDate?: string;
  onPaymentAdded: (updatedPlan: Plan) => void;
  trigger?: React.ReactElement;
}

export function AddRecurringExtraPaymentDialog({
  planId,
  defaultDate,
  onPaymentAdded,
  trigger,
}: AddRecurringExtraPaymentDialogProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [startDate, setStartDate] = useState(defaultDate || toDateValue(new Date()));
  const [amount, setAmount] = useState("200");
  const [count, setCount] = useState("12");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError("Please enter a valid amount greater than 0");
      return;
    }
    const numCount = parseInt(count, 10);
    if (isNaN(numCount) || numCount < 1 || numCount > 600) {
      setError("Count must be between 1 and 600 occurrences");
      return;
    }
    if (!startDate) {
      setError("Please select a start date");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const updatedPlan = await plansApi.addRecurringExtraPayment(planId, {
        start_date: startDate,
        amount: numAmount,
        count: numCount,
      });
      setOpen(false);
      onPaymentAdded(updatedPlan);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add recurring extra payment");
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
              <RepeatIcon data-icon="inline-start" />
              Add Recurring Extra Payment
            </Button>
          )
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Recurring Extra Payment</DialogTitle>
          <DialogDescription>
            Apply an extra principal payment repeatedly across multiple monthly installments.
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
              <FieldLabel htmlFor="rec-start-date">First Payment Date</FieldLabel>
              <DatePicker id="rec-start-date" value={startDate} onValueChange={setStartDate} required />
            </Field>

            <Field>
              <FieldLabel htmlFor="rec-amount">Monthly Extra Amount ($)</FieldLabel>
              <Input
                id="rec-amount"
                type="number"
                step="0.01"
                min="1"
                placeholder="200"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </Field>

            <Field>
              <FieldLabel htmlFor="rec-count">Number of Payments (Months)</FieldLabel>
              <Input
                id="rec-count"
                type="number"
                min="1"
                max="600"
                placeholder="12"
                value={count}
                onChange={(e) => setCount(e.target.value)}
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
              {loading ? "Adding..." : "Add Recurring Payment"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
