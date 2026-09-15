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
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { plansApi, type UpdatePlanPayload } from "@/lib/plans-api";
import { Edit3Icon } from "lucide-react";
import type { InterestRateApplication, Plan } from "@/lib/types";

interface EditPlanDialogProps {
  plan: Plan;
  onPlanUpdated: (plan: Plan) => void;
  trigger?: React.ReactElement;
}

export function EditPlanDialog({ plan, onPlanUpdated, trigger }: EditPlanDialogProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState(plan.name);
  const [amount, setAmount] = useState(String(plan.amount));
  const [interestRate, setInterestRate] = useState(String(plan.interest_rate));
  const [years, setYears] = useState(String(plan.term.years));
  const [months, setMonths] = useState(String(plan.term.months));
  const [startDate, setStartDate] = useState(plan.start_date);
  const [fixedFee, setFixedFee] = useState(String(plan.early_payment_fees?.fixed ?? "0"));
  const [percentFee, setPercentFee] = useState(String(plan.early_payment_fees?.percent ?? "0"));
  const [application, setApplication] = useState<InterestRateApplication>(
    plan.interest_rate_application || "whole_month",
  );

  function resetForm() {
    setName(plan.name);
    setAmount(String(plan.amount));
    setInterestRate(String(plan.interest_rate));
    setYears(String(plan.term.years));
    setMonths(String(plan.term.months));
    setStartDate(plan.start_date);
    setFixedFee(String(plan.early_payment_fees?.fixed ?? "0"));
    setPercentFee(String(plan.early_payment_fees?.percent ?? "0"));
    setApplication(plan.interest_rate_application || "whole_month");
    setError(null);
  }

  function handleOpenChange(nextOpen: boolean) {
    if (nextOpen) resetForm();
    setOpen(nextOpen);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Plan name is required");
      return;
    }

    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError("Please enter a valid loan amount greater than 0");
      return;
    }

    const numRate = parseFloat(interestRate);
    if (isNaN(numRate) || numRate < 0 || numRate > 100) {
      setError("Interest rate must be between 0% and 100%");
      return;
    }

    const numYears = parseInt(years, 10) || 0;
    const numMonths = parseInt(months, 10) || 0;
    if (numYears === 0 && numMonths === 0) {
      setError("Term must be at least one month");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload: UpdatePlanPayload = {
        name: name.trim(),
        amount: numAmount,
        interest_rate: numRate,
        term: {
          years: numYears,
          months: numMonths,
        },
        start_date: startDate || undefined,
        early_payment_fees: {
          fixed: parseFloat(fixedFee) || 0,
          percent: parseFloat(percentFee) || 0,
        },
        interest_rate_application: application,
      };

      const updated = await plansApi.updatePlan(plan.id, payload);
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
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit Loan Plan</DialogTitle>
          <DialogDescription>Update the baseline parameters for this loan plan.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="edit-plan-name">Plan Name</FieldLabel>
              <Input id="edit-plan-name" value={name} onChange={(e) => setName(e.target.value)} required />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel htmlFor="edit-plan-amount">Principal Amount ($)</FieldLabel>
                <Input
                  id="edit-plan-amount"
                  type="number"
                  step="0.01"
                  min="1"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  required
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="edit-plan-rate">Annual Interest Rate (%)</FieldLabel>
                <Input
                  id="edit-plan-rate"
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={interestRate}
                  onChange={(e) => setInterestRate(e.target.value)}
                  required
                />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel htmlFor="edit-plan-years">Term (Years)</FieldLabel>
                <Input
                  id="edit-plan-years"
                  type="number"
                  min="0"
                  max="50"
                  value={years}
                  onChange={(e) => setYears(e.target.value)}
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="edit-plan-months">Term (Extra Months)</FieldLabel>
                <Input
                  id="edit-plan-months"
                  type="number"
                  min="0"
                  max="11"
                  value={months}
                  onChange={(e) => setMonths(e.target.value)}
                />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel htmlFor="edit-plan-start">Start Date</FieldLabel>
                <DatePicker id="edit-plan-start" value={startDate} onValueChange={setStartDate} required />
              </Field>

              <Field>
                <FieldLabel htmlFor="edit-plan-application">Interest Rate Application</FieldLabel>
                <Select
                  value={application}
                  onValueChange={(val) => val && setApplication(val as InterestRateApplication)}
                >
                  <SelectTrigger id="edit-plan-application" className="w-full">
                    <SelectValue placeholder="Select application" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="whole_month">Whole Month</SelectItem>
                      <SelectItem value="prorated_days">Prorated (Days)</SelectItem>
                      <SelectItem value="prorated_payment_period">Prorated (Period)</SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel htmlFor="edit-plan-fee-fixed">Early Payoff Fee ($ Fixed)</FieldLabel>
                <Input
                  id="edit-plan-fee-fixed"
                  type="number"
                  step="0.01"
                  min="0"
                  value={fixedFee}
                  onChange={(e) => setFixedFee(e.target.value)}
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="edit-plan-fee-pct">Early Payoff Fee (% Rate)</FieldLabel>
                <Input
                  id="edit-plan-fee-pct"
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={percentFee}
                  onChange={(e) => setPercentFee(e.target.value)}
                />
              </Field>
            </div>
          </FieldGroup>

          <DialogFooter className="mt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading && <Spinner data-icon="inline-start" />}
              {loading ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
