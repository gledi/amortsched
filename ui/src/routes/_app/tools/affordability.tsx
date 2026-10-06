import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { createFileRoute, useRouter } from "@tanstack/react-router";
import { HomeIcon } from "lucide-react";
import { CreatePlanDialog } from "@/components/CreatePlanDialog";
import { NumberField } from "@/components/NumberField";
import { ResultStat, ToolPage } from "@/components/tools/ToolLayout";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableFooter, TableRow } from "@/components/ui/table";
import { useDefaultCurrency } from "@/hooks/use-default-currency";
import { CURRENCIES } from "@/lib/currency";
import { formatCurrency, formatPercent } from "@/lib/formatters";
import { toolsApi, type AffordabilityRequest, type AffordabilityResult } from "@/lib/tools-api";

export const Route = createFileRoute("/_app/tools/affordability")({
  component: AffordabilityPage,
});

const DEFAULTS = {
  income: "9000",
  debts: "400",
  downPayment: "60000",
  rate: "6.5",
  years: "30",
  taxRate: "1.1",
  insurance: "1500",
  hoa: "0",
  pmi: "0.5",
  frontEnd: "28",
  backEnd: "36",
};

type FormState = typeof DEFAULTS;

function toRequest(form: FormState): AffordabilityRequest {
  const n = (value: string) => (value.trim() === "" ? 0 : Number(value));
  return {
    gross_monthly_income: n(form.income),
    monthly_debts: n(form.debts),
    down_payment: n(form.downPayment),
    interest_rate: n(form.rate),
    term_months: Math.round(n(form.years) * 12),
    property_tax_rate: n(form.taxRate),
    insurance_annual: n(form.insurance),
    hoa_monthly: n(form.hoa),
    pmi_annual_rate: n(form.pmi),
    front_end_ratio: n(form.frontEnd),
    back_end_ratio: n(form.backEnd),
  };
}

function AffordabilityResults({
  result,
  form,
  currency,
}: {
  result: AffordabilityResult;
  form: FormState;
  currency: string;
}) {
  const router = useRouter();
  const money = (value: string | number | null) => formatCurrency(value, currency);
  const price = Number(result.max_home_price);
  const monthly = result.monthly;
  const breakdown = [
    { label: "Principal & interest", value: monthly.principal_interest },
    { label: "Property tax", value: monthly.property_tax },
    { label: "Home insurance", value: monthly.insurance },
    { label: "HOA dues", value: monthly.hoa },
    { label: "PMI", value: monthly.pmi },
  ].filter((row) => Number(row.value) > 0);

  if (price <= 0) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          With these debts, the {result.limiting_ratio === "back_end" ? "total debt" : "housing"} limit leaves no room
          for a mortgage payment. Pay down debts, raise the down payment, or adjust the ratios.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardDescription>You can likely afford a home up to</CardDescription>
          <CardTitle className="text-3xl font-bold tabular-nums text-primary">{money(price)}</CardTitle>
          <p className="text-sm text-muted-foreground">
            {money(form.downPayment)} down ({formatPercent(result.down_payment_percent)}) with a{" "}
            {money(result.max_loan_amount)} loan, at {money(monthly.total)} a month.
          </p>
        </CardHeader>
        <CardContent>
          <CreatePlanDialog
            initialValues={{
              name: `Home at ${money(price)}`,
              loanType: "mortgage",
              currency,
              homePrice: String(price),
              downPayment: form.downPayment,
              interestRate: form.rate,
              years: form.years,
              months: "0",
              propertyTaxAnnual: ((price * Number(form.taxRate)) / 100).toFixed(2),
              insuranceAnnual: form.insurance,
              hoaMonthly: form.hoa,
              pmiRate: Number(result.ltv) > 80 ? form.pmi : "0",
            }}
            onPlanCreated={(plan) => router.navigate({ to: "/plans/$planId", params: { planId: plan.id } })}
            trigger={
              <Button variant="outline" size="sm">
                <HomeIcon data-icon="inline-start" />
                Plan a mortgage at this price
              </Button>
            }
          />
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-3">
        <ResultStat
          label="Housing / income"
          value={formatPercent(result.front_end_ratio)}
          detail={`Limit ${formatPercent(form.frontEnd)}`}
        />
        <ResultStat
          label="All debts / income"
          value={formatPercent(result.back_end_ratio)}
          detail={`Limit ${formatPercent(form.backEnd)}`}
        />
        <ResultStat
          label="Loan-to-value"
          value={formatPercent(result.ltv)}
          detail={Number(result.ltv) > 80 ? "PMI required above 80%" : "No PMI needed"}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Monthly payment</CardTitle>
          <CardDescription>
            Limited by the {result.limiting_ratio === "front_end" ? "housing-cost" : "total-debt"} ratio: at most{" "}
            {money(result.max_monthly_housing)} a month for housing.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableBody>
              {breakdown.map((row) => (
                <TableRow key={row.label}>
                  <TableCell>{row.label}</TableCell>
                  <TableCell className="text-right font-mono">{money(row.value)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell>Total</TableCell>
                <TableCell className="text-right font-mono">{money(monthly.total)}</TableCell>
              </TableRow>
            </TableFooter>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function AffordabilityPage() {
  const defaultCurrency = useDefaultCurrency();
  const [currency, setCurrency] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(DEFAULTS);
  const [submitted, setSubmitted] = useState<FormState>(DEFAULTS);
  const set = (patch: Partial<FormState>) => setForm((current) => ({ ...current, ...patch }));
  const activeCurrency = currency ?? defaultCurrency;

  const calculate = useMutation({ mutationFn: toolsApi.affordability });
  const { mutate } = calculate;
  const ran = useRef(false);
  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    mutate(toRequest(DEFAULTS));
  }, [mutate]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitted(form);
    calculate.mutate(toRequest(form));
  }

  return (
    <ToolPage
      title="How much home can I afford?"
      description="Lenders usually cap housing costs at 28% of gross income and all debt payments at 36%. This finds the highest price that fits both, including taxes, insurance, and PMI."
    >
      <Card>
        <CardContent className="pt-4">
          <form onSubmit={submit}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="afford-currency">Currency</FieldLabel>
                <Select value={activeCurrency} onValueChange={(value) => value && setCurrency(value)}>
                  <SelectTrigger id="afford-currency" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {CURRENCIES.map((option) => (
                        <SelectItem key={option.code} value={option.code}>
                          {option.code} · {option.name}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>
              <FieldSet>
                <FieldLegend variant="label">You</FieldLegend>
                <div className="grid grid-cols-2 gap-3">
                  <NumberField
                    id="afford-income"
                    label="Gross income / month"
                    value={form.income}
                    onChange={(income) => set({ income })}
                  />
                  <NumberField
                    id="afford-debts"
                    label="Debt payments / month"
                    value={form.debts}
                    onChange={(debts) => set({ debts })}
                    description="Car, student, cards"
                  />
                  <NumberField
                    id="afford-down"
                    label="Down payment"
                    value={form.downPayment}
                    onChange={(downPayment) => set({ downPayment })}
                  />
                </div>
              </FieldSet>
              <FieldSet>
                <FieldLegend variant="label">The loan</FieldLegend>
                <div className="grid grid-cols-2 gap-3">
                  <NumberField id="afford-rate" label="Rate (%)" value={form.rate} onChange={(rate) => set({ rate })} />
                  <NumberField
                    id="afford-years"
                    label="Term (years)"
                    value={form.years}
                    step="1"
                    min="1"
                    max="50"
                    onChange={(years) => set({ years })}
                  />
                  <NumberField id="afford-pmi" label="PMI (%/yr)" value={form.pmi} onChange={(pmi) => set({ pmi })} />
                </div>
              </FieldSet>
              <FieldSet>
                <FieldLegend variant="label">The home</FieldLegend>
                <div className="grid grid-cols-2 gap-3">
                  <NumberField
                    id="afford-tax"
                    label="Property tax (%/yr)"
                    value={form.taxRate}
                    onChange={(taxRate) => set({ taxRate })}
                  />
                  <NumberField
                    id="afford-insurance"
                    label="Insurance / year"
                    value={form.insurance}
                    onChange={(insurance) => set({ insurance })}
                  />
                  <NumberField id="afford-hoa" label="HOA / month" value={form.hoa} onChange={(hoa) => set({ hoa })} />
                </div>
              </FieldSet>
              <FieldSet>
                <FieldLegend variant="label">Lender limits</FieldLegend>
                <div className="grid grid-cols-2 gap-3">
                  <NumberField
                    id="afford-front"
                    label="Housing (%)"
                    value={form.frontEnd}
                    onChange={(frontEnd) => set({ frontEnd })}
                  />
                  <NumberField
                    id="afford-back"
                    label="All debts (%)"
                    value={form.backEnd}
                    onChange={(backEnd) => set({ backEnd })}
                  />
                </div>
              </FieldSet>
              <Button type="submit" disabled={calculate.isPending}>
                {calculate.isPending ? "Calculating..." : "Calculate"}
              </Button>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>

      <div>
        {calculate.isError ? (
          <Alert variant="destructive">
            <AlertDescription>{calculate.error.message}</AlertDescription>
          </Alert>
        ) : calculate.data ? (
          <AffordabilityResults result={calculate.data} form={submitted} currency={activeCurrency} />
        ) : null}
      </div>
    </ToolPage>
  );
}
