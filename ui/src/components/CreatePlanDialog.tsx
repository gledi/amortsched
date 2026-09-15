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
import { plansApi, type CreatePlanPayload } from "@/lib/plans-api";
import { toDateValue } from "@/lib/date-value";
import { PlusIcon } from "lucide-react";
import type { InterestRateApplication, Plan } from "@/lib/types";

interface CreatePlanDialogProps {
  onPlanCreated: (plan: Plan) => void;
  trigger?: React.ReactElement;
}

export function CreatePlanDialog({ onPlanCreated, trigger }: CreatePlanDialogProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("300000");
  const [interestRate, setInterestRate] = useState("6.5");
  const [years, setYears] = useState("30");
  const [months, setMonths] = useState("0");
  const [startDate, setStartDate] = useState(() => toDateValue(new Date()));
  const [fixedFee, setFixedFee] = useState("0");
  const [percentFee, setPercentFee] = useState("0");
  const [application, setApplication] = useState<InterestRateApplication>("whole_month");

  function resetForm() {
    setName("");
    setAmount("300000");
    setInterestRate("6.5");
    setYears("30");
    setMonths("0");
    setStartDate(toDateValue(new Date()));
    setFixedFee("0");
    setPercentFee("0");
    setApplication("whole_month");
    setError(null);
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
      const payload: CreatePlanPayload = {
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

      const newPlan = await plansApi.createPlan(payload);
      setOpen(false);
      resetForm();
      onPlanCreated(newPlan);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create plan");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          trigger ?? (
            <Button>
              <PlusIcon data-icon="inline-start" />
              New Loan Plan
            </Button>
          )
        }
      />
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Loan Plan</DialogTitle>
          <DialogDescription>Configure the baseline parameters for your loan amortization schedule.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="plan-name">Plan Name</FieldLabel>
              <Input
                id="plan-name"
                placeholder="e.g. 30-Year Fixed Mortgage"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel htmlFor="plan-amount">Principal Amount ($)</FieldLabel>
                <Input
                  id="plan-amount"
                  type="number"
                  step="0.01"
                  min="1"
                  placeholder="300000"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  required
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="plan-rate">Annual Interest Rate (%)</FieldLabel>
                <Input
                  id="plan-rate"
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  placeholder="6.5"
                  value={interestRate}
                  onChange={(e) => setInterestRate(e.target.value)}
                  required
                />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel htmlFor="plan-years">Term (Years)</FieldLabel>
                <Input
                  id="plan-years"
                  type="number"
                  min="0"
                  max="50"
                  placeholder="30"
                  value={years}
                  onChange={(e) => setYears(e.target.value)}
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="plan-months">Term (Extra Months)</FieldLabel>
                <Input
                  id="plan-months"
                  type="number"
                  min="0"
                  max="11"
                  placeholder="0"
                  value={months}
                  onChange={(e) => setMonths(e.target.value)}
                />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel htmlFor="plan-start">Start Date</FieldLabel>
                <DatePicker id="plan-start" value={startDate} onValueChange={setStartDate} required />
              </Field>

              <Field>
                <FieldLabel htmlFor="plan-application">Interest Rate Application</FieldLabel>
                <Select
                  value={application}
                  onValueChange={(val) => val && setApplication(val as InterestRateApplication)}
                >
                  <SelectTrigger id="plan-application" className="w-full">
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
                <FieldLabel htmlFor="plan-fee-fixed">Early Payoff Fee ($ Fixed)</FieldLabel>
                <Input
                  id="plan-fee-fixed"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={fixedFee}
                  onChange={(e) => setFixedFee(e.target.value)}
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="plan-fee-pct">Early Payoff Fee (% Rate)</FieldLabel>
                <Input
                  id="plan-fee-pct"
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  placeholder="0.00"
                  value={percentFee}
                  onChange={(e) => setPercentFee(e.target.value)}
                />
              </Field>
            </div>
          </FieldGroup>

          <DialogFooter className="mt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setOpen(false);
                resetForm();
              }}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading && <Spinner data-icon="inline-start" />}
              {loading ? "Creating..." : "Create Plan"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
