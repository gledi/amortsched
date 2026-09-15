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
import { PlusIcon } from "lucide-react";
import type { Plan } from "@/lib/types";

interface AddExtraPaymentDialogProps {
  planId: string;
  defaultDate?: string;
  onPaymentAdded: (updatedPlan: Plan) => void;
  trigger?: React.ReactElement;
}

export function AddExtraPaymentDialog({ planId, defaultDate, onPaymentAdded, trigger }: AddExtraPaymentDialogProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [date, setDate] = useState(defaultDate || toDateValue(new Date()));
  const [amount, setAmount] = useState("1000");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError("Please enter a valid amount greater than 0");
      return;
    }
    if (!date) {
      setError("Please select a date");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const updatedPlan = await plansApi.addExtraPayment(planId, {
        date,
        amount: numAmount,
      });
      setOpen(false);
      onPaymentAdded(updatedPlan);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add extra payment");
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
              <PlusIcon data-icon="inline-start" />
              Add One-Time Extra Payment
            </Button>
          )
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add One-Time Extra Payment</DialogTitle>
          <DialogDescription>Inject an additional lump-sum principal payment on a specific date.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="extra-date">Payment Date</FieldLabel>
              <DatePicker id="extra-date" value={date} onValueChange={setDate} required />
            </Field>

            <Field>
              <FieldLabel htmlFor="extra-amount">Extra Amount ($)</FieldLabel>
              <Input
                id="extra-amount"
                type="number"
                step="0.01"
                min="1"
                placeholder="1000"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
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
              {loading ? "Adding..." : "Add Payment"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
