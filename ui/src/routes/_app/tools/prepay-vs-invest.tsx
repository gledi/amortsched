import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import { NumberField } from "@/components/NumberField";
import { LoanSourcePicker, type LoanSource } from "@/components/tools/LoanSourcePicker";
import { ResultStat, ToolPage } from "@/components/tools/ToolLayout";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartLegendContent, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { ChartLegend, ChartTooltip } from "@/components/ui/chart-primitives";
import { FieldGroup, FieldLegend, FieldSet } from "@/components/ui/field";
import { useDefaultCurrency } from "@/hooks/use-default-currency";
import { formatCompactCurrency, formatCurrency, formatMonths, formatPercent } from "@/lib/formatters";
import { toolsApi, type PrepayVsInvestRequest, type PrepayVsInvestResult } from "@/lib/tools-api";

export const Route = createFileRoute("/_app/tools/prepay-vs-invest")({
  validateSearch: (search: Record<string, unknown>): { plan?: string } => ({
    plan: typeof search.plan === "string" ? search.plan : undefined,
  }),
  component: PrepayVsInvestPage,
});

const chartConfig = {
  prepay: { label: "Prepay the loan", color: "var(--series-1)" },
  invest: { label: "Invest the extra", color: "var(--series-2)" },
} satisfies ChartConfig;

function NetWorthChart({ result, currency }: { result: PrepayVsInvestResult; currency: string }) {
  const rows = result.timeline
    .filter((point) => point.month % 3 === 0 || point.month === result.timeline.length)
    .map((point) => ({ month: point.month, prepay: Number(point.prepay), invest: Number(point.invest) }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Net worth from this money</CardTitle>
        <CardDescription>Investments minus what you still owe on the loan, for each strategy.</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-72 w-full">
          <LineChart accessibilityLayer data={rows} margin={{ top: 12, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="month"
              type="number"
              domain={["dataMin", "dataMax"]}
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
            <ChartTooltip
              content={
                <ChartTooltipContent
                  labelFormatter={(_, payload) => `After ${formatMonths(Number(payload?.[0]?.payload?.month ?? 0))}`}
                  formatter={(value, name) => (
                    <div className="flex w-full items-center justify-between gap-4">
                      <span>{chartConfig[name as keyof typeof chartConfig]?.label ?? name}</span>
                      <span className="font-mono tabular-nums">{formatCurrency(Number(value), currency)}</span>
                    </div>
                  )}
                />
              }
            />
            <ChartLegend content={<ChartLegendContent />} />
            <Line
              dataKey="prepay"
              type="monotone"
              stroke="var(--color-prepay)"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              dataKey="invest"
              type="monotone"
              stroke="var(--color-invest)"
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

function headline(result: PrepayVsInvestResult, currency: string): string {
  const amount = formatCurrency(result.advantage, currency);
  if (result.better_strategy === "tie") return "Both strategies end up the same";
  return result.better_strategy === "prepay"
    ? `Prepaying leaves you ${amount} better off`
    : `Investing leaves you ${amount} better off`;
}

function PrepayResults({ result, currency }: { result: PrepayVsInvestResult; currency: string }) {
  const money = (value: string | number) => formatCurrency(value, currency);
  const years = formatMonths(result.loan.term_months);
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardDescription>After {years}, comparing net worth from the same monthly money</CardDescription>
          <CardTitle className="text-2xl font-bold">{headline(result, currency)}</CardTitle>
          <p className="text-sm text-muted-foreground">
            {result.break_even_return !== null
              ? `Investing wins only if returns beat ${formatPercent(result.break_even_return)} a year after taxes and fees. The loan's rate is ${formatPercent(result.loan.interest_rate)}, a guaranteed return.`
              : "This holds across any plausible return."}
          </p>
        </CardHeader>
      </Card>
      <div className="grid gap-3 sm:grid-cols-3">
        <ResultStat label="Interest saved by prepaying" value={money(result.interest_saved)} tone="good" />
        <ResultStat label="Paid off sooner by" value={formatMonths(result.months_saved)} />
        <ResultStat label="Regular payment" value={money(result.regular_payment)} />
        <ResultStat label="Net worth if you prepay" value={money(result.prepay_net_worth)} />
        <ResultStat label="Net worth if you invest" value={money(result.invest_net_worth)} />
        <ResultStat
          label="Loan"
          value={money(result.loan.principal)}
          detail={`${formatPercent(result.loan.interest_rate)} over ${years}`}
        />
      </div>
      <NetWorthChart result={result} currency={currency} />
    </div>
  );
}

function PrepayVsInvestPage() {
  const search = Route.useSearch();
  const defaultCurrency = useDefaultCurrency();
  const [source, setSource] = useState<LoanSource>(search.plan ? "plan" : "manual");
  const [planId, setPlanId] = useState(search.plan ?? "");
  const [form, setForm] = useState({ principal: "300000", rate: "6", years: "30", extra: "300", annualReturn: "7" });
  const set = (patch: Partial<typeof form>) => setForm((current) => ({ ...current, ...patch }));

  const calculate = useMutation({ mutationFn: (body: PrepayVsInvestRequest) => toolsApi.prepayVsInvest(body) });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const shared = { extra_monthly: Number(form.extra), annual_return: Number(form.annualReturn) };
    calculate.mutate(
      source === "plan"
        ? { ...shared, plan_id: planId }
        : {
            ...shared,
            principal: Number(form.principal),
            interest_rate: Number(form.rate),
            term_months: Math.round(Number(form.years) * 12),
          },
    );
  }

  const currency = calculate.data?.loan.currency ?? defaultCurrency;

  return (
    <ToolPage
      title="Prepay or invest?"
      description="Put the same extra money each month toward the loan, or invest it. Once the loan is gone, the prepayer invests the whole former payment. Whoever has more at the end of the original term wins."
    >
      <Card>
        <CardContent className="pt-4">
          <form onSubmit={submit}>
            <FieldGroup>
              <FieldSet>
                <FieldLegend variant="label">The loan</FieldLegend>
                <LoanSourcePicker source={source} onSourceChange={setSource} planId={planId} onPlanChange={setPlanId} />
                {source === "manual" ? (
                  <div className="grid grid-cols-2 gap-3">
                    <NumberField
                      id="prepay-principal"
                      label="Loan amount"
                      value={form.principal}
                      onChange={(principal) => set({ principal })}
                    />
                    <NumberField
                      id="prepay-rate"
                      label="Rate (%)"
                      value={form.rate}
                      onChange={(rate) => set({ rate })}
                    />
                    <NumberField
                      id="prepay-years"
                      label="Term (years)"
                      value={form.years}
                      step="1"
                      min="1"
                      onChange={(years) => set({ years })}
                    />
                  </div>
                ) : null}
              </FieldSet>
              <FieldSet>
                <FieldLegend variant="label">The extra money</FieldLegend>
                <div className="grid grid-cols-2 gap-3">
                  <NumberField
                    id="prepay-extra"
                    label="Extra / month"
                    value={form.extra}
                    onChange={(extra) => set({ extra })}
                  />
                  <NumberField
                    id="prepay-return"
                    label="Expected return (%/yr)"
                    value={form.annualReturn}
                    min="-50"
                    max="50"
                    onChange={(annualReturn) => set({ annualReturn })}
                  />
                </div>
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
          <PrepayResults result={calculate.data} currency={currency} />
        ) : (
          <Card>
            <CardContent className="py-12 text-center text-sm text-muted-foreground">
              Enter a loan and how much extra you could put toward it each month.
            </CardContent>
          </Card>
        )}
      </div>
    </ToolPage>
  );
}
