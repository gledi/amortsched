import * as React from "react";
import { useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DatePicker } from "@/components/ui/date-picker";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import {
  parseAdjustment,
  toFormValues,
  type AdjustmentFormValues,
  type AdjustmentKind,
  type AdjustmentValue,
} from "@/lib/adjustments";

const COPY: Record<AdjustmentKind, { title: string; description: string; dateLabel: string }> = {
  one_time: {
    title: "One-time extra payment",
    description: "A lump sum applied to principal on a specific date.",
    dateLabel: "Payment date",
  },
  recurring: {
    title: "Recurring extra payment",
    description: "A fixed extra amount paid toward principal every month.",
    dateLabel: "First payment",
  },
  rate_change: {
    title: "Interest rate change",
    description: "A new annual rate from this date onward, e.g. when a fixed period ends.",
    dateLabel: "Effective date",
  },
};

interface AdjustmentDialogProps {
  kind: AdjustmentKind;
  initial?: AdjustmentValue;
  defaultDate: string;
  trigger: React.ReactElement;
  onSubmit: (value: AdjustmentValue) => Promise<void>;
}

export function AdjustmentDialog({ kind, initial, defaultDate, trigger, onSubmit }: AdjustmentDialogProps) {
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState<AdjustmentFormValues>(() => toFormValues(kind, initial, defaultDate));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const copy = COPY[kind];

  function handleOpenChange(next: boolean) {
    if (next) {
      setValues(toFormValues(kind, initial, defaultDate));
      setError(null);
    }
    setOpen(next);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const parsed = parseAdjustment(kind, values);
    if ("error" in parsed) {
      setError(parsed.error);
      return;
    }
    setSaving(true);
    try {
      await onSubmit(parsed.value);
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the change");
    } finally {
      setSaving(false);
    }
  }

  const set = (patch: Partial<AdjustmentFormValues>) => setValues((current) => ({ ...current, ...patch }));

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={trigger} />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{initial ? `Edit ${copy.title.toLowerCase()}` : copy.title}</DialogTitle>
          <DialogDescription>{copy.description}</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error ? (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor={`adjustment-${kind}-date`}>{copy.dateLabel}</FieldLabel>
              <DatePicker id={`adjustment-${kind}-date`} value={values.date} onValueChange={(date) => set({ date })} />
            </Field>
            {kind === "rate_change" ? (
              <Field>
                <FieldLabel htmlFor="adjustment-rate">New annual rate (%)</FieldLabel>
                <Input
                  id="adjustment-rate"
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={values.rate}
                  onChange={(event) => set({ rate: event.target.value })}
                />
              </Field>
            ) : (
              <div className={kind === "recurring" ? "grid grid-cols-2 gap-3" : undefined}>
                <Field>
                  <FieldLabel htmlFor={`adjustment-${kind}-amount`}>
                    {kind === "recurring" ? "Extra per month" : "Amount"}
                  </FieldLabel>
                  <Input
                    id={`adjustment-${kind}-amount`}
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={values.amount}
                    onChange={(event) => set({ amount: event.target.value })}
                  />
                </Field>
                {kind === "recurring" ? (
                  <Field>
                    <FieldLabel htmlFor="adjustment-count">Number of payments</FieldLabel>
                    <Input
                      id="adjustment-count"
                      type="number"
                      step="1"
                      min="1"
                      max="600"
                      value={values.count}
                      onChange={(event) => set({ count: event.target.value })}
                    />
                  </Field>
                ) : null}
              </div>
            )}
          </FieldGroup>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? <Spinner data-icon="inline-start" /> : null}
              {initial ? "Save" : "Add"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
