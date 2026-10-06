import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { CartesianGrid, Line, LineChart, ReferenceLine, XAxis, YAxis } from "recharts";
import { NumberField } from "@/components/NumberField";
import { LoanSourcePicker, type LoanSource } from "@/components/tools/LoanSourcePicker";
import { ResultStat, ToolPage } from "@/components/tools/ToolLayout";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { ChartTooltip } from "@/components/ui/chart-primitives";
import { Checkbox } from "@/components/ui/checkbox";
import { DatePicker } from "@/components/ui/date-picker";
import { Field, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field";
import { useDefaultCurrency } from "@/hooks/use-default-currency";
import { toDateValue } from "@/lib/date-value";
import { formatCompactCurrency, formatCurrency, formatMonths, formatPercent } from "@/lib/formatters";
import { toolsApi, type RefinanceRequest, type RefinanceResult } from "@/lib/tools-api";

export const Route = createFileRoute("/_app/tools/refinance")({
  validateSearch: (search: Record<string, unknown>): { plan?: string } => ({
    plan: typeof search.plan === "string" ? search.plan : undefined,
  }),
  component: RefinancePage,
});

const chartConfig = { advantage: { label: "Ahead by refinancing", color: "var(--series-1)" } } satisfies ChartConfig;

function AdvantageChart({ result, currency }: { result: RefinanceResult; currency: string }) {
  const series = result.advantage_by_month;
  const step = series.length > 120 ? 3 : 1;
  const rows = series
    .map((value, month) => ({ month, advantage: Number(value) }))
    .filter((row) => row.month % step === 0 || row.month === series.length - 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Net position over time</CardTitle>
        <CardDescription>
          How far ahead (above zero) or behind you are by refinancing, counting payments made, closing costs, and what
          you still owe.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-72 w-full">
          <LineChart accessibilityLayer data={rows} margin={{ top: 12, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="month"
              type="number"
              domain={[0, "dataMax"]}
              ticks={rows.filter((row) => row.month % 60 === 0).map((row) => row.month)}
              tickFormatter={(month: number) => `${month / 12}y`}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={72}
              tickFormatter={(value: number) => formatCompactCurrency(value, currency)}
            />
            <ReferenceLine y={0} stroke="var(--muted-foreground)" />
            {result.break_even_month !== null ? (
              <ReferenceLine
                x={result.break_even_month}
                stroke="var(--muted-foreground)"
                strokeDasharray="4 4"
                label={{
                  value: "Break-even",
                  position: "insideTopLeft",
                  fill: "var(--muted-foreground)",
                  fontSize: 11,
                }}
              />
            ) : null}
            <ChartTooltip
              content={
                <ChartTooltipContent
                  hideIndicator
                  labelFormatter={(_, payload) => `After ${formatMonths(Number(payload?.[0]?.payload?.month ?? 0))}`}
                  formatter={(value) => (
                    <div className="flex w-full items-center justify-between gap-4">
                      <span>{Number(value) >= 0 ? "Ahead by" : "Behind by"}</span>
                      <span className="font-mono tabular-nums">
                        {formatCurrency(Math.abs(Number(value)), currency)}
                      </span>
                    </div>
                  )}
                />
              }
            />
            <Line
              dataKey="advantage"
              type="monotone"
              stroke="var(--color-advantage)"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}

function RefinanceResults({ result, currency }: { result: RefinanceResult; currency: string }) {
  const money = (value: string | number) => formatCurrency(value, currency);
  const savings = Number(result.monthly_savings);
  const lifetime = Number(result.lifetime_savings);
  const current = result.current_loan;

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardDescription>
            Refinancing {money(current.balance)} at {formatPercent(current.rate)} with {current.remaining_months}{" "}
            payments left
          </CardDescription>
          <CardTitle className="text-2xl font-bold">
            {result.break_even_month !== null
              ? `Pays for itself after ${formatMonths(result.break_even_month)}`
              : "Never pays for itself"}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {result.break_even_month !== null
              ? "Keep the new loan at least this long for the refinance to come out ahead."
              : "Over the life of the loan you end up paying more than you would by keeping your current loan."}
          </p>
        </CardHeader>
      </Card>
      <div className="grid gap-3 sm:grid-cols-3">
        <ResultStat
          label="Monthly payment"
          value={money(result.new_payment)}
          detail={`Now ${money(result.current_payment)}`}
        />
        <ResultStat
          label={savings >= 0 ? "Saved each month" : "Extra each month"}
          value={money(Math.abs(savings))}
          tone={savings >= 0 ? "good" : "bad"}
        />
        <ResultStat
          label={lifetime >= 0 ? "Saved over the loan" : "Lost over the loan"}
          value={money(Math.abs(lifetime))}
          tone={lifetime >= 0 ? "good" : "bad"}
          detail="Total payments plus cash at closing"
        />
        <ResultStat
          label="Interest from here"
          value={money(result.new_total_interest)}
          detail={`Now ${money(result.current_total_interest)}`}
        />
        <ResultStat label="Cash at closing" value={money(result.cash_due_at_closing)} />
        <ResultStat label="New loan amount" value={money(result.new_principal)} />
      </div>
      <AdvantageChart result={result} currency={currency} />
    </div>
  );
}

function RefinancePage() {
  const search = Route.useSearch();
  const defaultCurrency = useDefaultCurrency();
  const [source, setSource] = useState<LoanSource>(search.plan ? "plan" : "manual");
  const [planId, setPlanId] = useState(search.plan ?? "");
  const [asOf, setAsOf] = useState(() => toDateValue(new Date()));
  const [form, setForm] = useState({
    balance: "300000",
    rate: "7",
    remainingYears: "25",
    newRate: "5.75",
    newYears: "25",
    closingCosts: "6000",
    roll: false,
  });
  const set = (patch: Partial<typeof form>) => setForm((current) => ({ ...current, ...patch }));

  const calculate = useMutation({ mutationFn: (body: RefinanceRequest) => toolsApi.refinance(body) });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const shared = {
      new_rate: Number(form.newRate),
      new_term_months: Math.round(Number(form.newYears) * 12),
      closing_costs: Number(form.closingCosts) || 0,
      roll_costs_into_loan: form.roll,
    };
    calculate.mutate(
      source === "plan"
        ? { ...shared, plan_id: planId, as_of: asOf }
        : {
            ...shared,
            current_balance: Number(form.balance),
            current_rate: Number(form.rate),
            remaining_months: Math.round(Number(form.remainingYears) * 12),
          },
    );
  }

  const currency = calculate.data?.current_loan.currency ?? defaultCurrency;

  return (
    <ToolPage
      title="Should I refinance?"
      description="Compares keeping your loan with taking a new one, month by month, so closing costs and a longer term are counted honestly."
    >
      <Card>
        <CardContent className="pt-4">
          <form onSubmit={submit}>
            <FieldGroup>
              <FieldSet>
                <FieldLegend variant="label">Your current loan</FieldLegend>
                <LoanSourcePicker source={source} onSourceChange={setSource} planId={planId} onPlanChange={setPlanId} />
                {source === "plan" ? (
                  <Field>
                    <FieldLabel htmlFor="refi-as-of">Refinance on</FieldLabel>
                    <DatePicker id="refi-as-of" value={asOf} onValueChange={setAsOf} />
                  </Field>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    <NumberField
                      id="refi-balance"
                      label="Balance"
                      value={form.balance}
                      onChange={(balance) => set({ balance })}
                    />
                    <NumberField id="refi-rate" label="Rate (%)" value={form.rate} onChange={(rate) => set({ rate })} />
                    <NumberField
                      id="refi-remaining"
                      label="Years left"
                      value={form.remainingYears}
                      step="0.5"
                      onChange={(remainingYears) => set({ remainingYears })}
                    />
                  </div>
                )}
              </FieldSet>
              <FieldSet>
                <FieldLegend variant="label">The new loan</FieldLegend>
                <div className="grid grid-cols-2 gap-3">
                  <NumberField
                    id="refi-new-rate"
                    label="Rate (%)"
                    value={form.newRate}
                    onChange={(newRate) => set({ newRate })}
                  />
                  <NumberField
                    id="refi-new-years"
                    label="Term (years)"
                    value={form.newYears}
                    step="1"
                    min="1"
                    onChange={(newYears) => set({ newYears })}
                  />
                  <NumberField
                    id="refi-costs"
                    label="Closing costs"
                    value={form.closingCosts}
                    onChange={(closingCosts) => set({ closingCosts })}
                  />
                </div>
                <Field orientation="horizontal">
                  <Checkbox
                    id="refi-roll"
                    checked={form.roll}
                    onCheckedChange={(checked) => set({ roll: checked === true })}
                  />
                  <FieldLabel htmlFor="refi-roll">Add closing costs to the new loan</FieldLabel>
                </Field>
              </FieldSet>
              <Button type="submit" disabled={calculate.isPending || (source === "plan" && !planId)}>
                {calculate.isPending ? "Calculating..." : "Compare"}
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
          <RefinanceResults result={calculate.data} currency={currency} />
        ) : (
          <Card>
            <CardContent className="py-12 text-center text-sm text-muted-foreground">
              Enter your current loan and the offer you got, then compare.
            </CardContent>
          </Card>
        )}
      </div>
    </ToolPage>
  );
}
