import { useQuery } from "@tanstack/react-query";
import { Field, FieldLabel } from "@/components/ui/field";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatCurrency } from "@/lib/formatters";
import { plansApi } from "@/lib/plans-api";

export type LoanSource = "plan" | "manual";

interface LoanSourcePickerProps {
  source: LoanSource;
  onSourceChange: (source: LoanSource) => void;
  planId: string;
  onPlanChange: (planId: string) => void;
}

export function LoanSourcePicker({ source, onSourceChange, planId, onPlanChange }: LoanSourcePickerProps) {
  const { data: plans = [] } = useQuery({ queryKey: ["plans"], queryFn: plansApi.listPlans });
  const selected = plans.find((plan) => plan.id === planId);

  return (
    <div className="flex flex-col gap-3">
      <Tabs value={source} onValueChange={(value) => value && onSourceChange(value as LoanSource)}>
        <TabsList className="w-full">
          <TabsTrigger value="plan" disabled={plans.length === 0}>
            One of my plans
          </TabsTrigger>
          <TabsTrigger value="manual">Enter details</TabsTrigger>
        </TabsList>
      </Tabs>
      {source === "plan" ? (
        <Field>
          <FieldLabel htmlFor="loan-source-plan">Plan</FieldLabel>
          <Select value={planId} onValueChange={(value) => value && onPlanChange(value)}>
            <SelectTrigger id="loan-source-plan" className="w-full">
              <SelectValue placeholder="Choose a plan">
                {selected
                  ? `${selected.lender || selected.name} · ${formatCurrency(selected.amount, selected.currency)}`
                  : null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {plans.map((plan) => (
                  <SelectItem key={plan.id} value={plan.id}>
                    {plan.lender || plan.name} · {formatCurrency(plan.amount, plan.currency)}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </Field>
      ) : null}
    </div>
  );
}
