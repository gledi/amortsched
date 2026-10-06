import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartLegendContent, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { ChartLegend, ChartTooltip } from "@/components/ui/chart-primitives";
import { chartLabel } from "@/lib/comparison-presentation";
import { formatCompactCurrency, formatCurrency } from "@/lib/formatters";
import type { PlanComparison } from "@/lib/types";

const chartConfig = {
  principal: { label: "Principal", color: "var(--chart-1)" },
  interest: { label: "Interest & fees", color: "var(--chart-2)" },
  upfrontFees: { label: "Upfront fees", color: "var(--chart-3)" },
  pmi: { label: "PMI", color: "var(--chart-4)" },
} satisfies ChartConfig;

export function PlanCostChart({ comparison, currency }: { comparison: PlanComparison; currency: string }) {
  const data = comparison.plans.map((plan) => ({
    label: chartLabel(plan),
    principal: Number(plan.total_principal),
    interest: Number(plan.total_interest) + Number(plan.schedule_fees),
    upfrontFees: Number(plan.upfront_fees),
    pmi: Number(plan.total_pmi),
  }));
  const hasPmi = data.some((row) => row.pmi > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Total cost by offer</CardTitle>
        <CardDescription>Everything you pay over the life of each loan, split by where the money goes.</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-80 w-full">
          <BarChart accessibilityLayer data={data} margin={{ top: 12, right: 12, bottom: 12, left: 12 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} interval={0} height={40} />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={72}
              tickFormatter={(value: number) => formatCompactCurrency(value, currency)}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
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
            <Bar
              dataKey="principal"
              stackId="cost"
              fill="var(--color-principal)"
              stroke="var(--background)"
              strokeWidth={2}
            />
            <Bar
              dataKey="interest"
              stackId="cost"
              fill="var(--color-interest)"
              stroke="var(--background)"
              strokeWidth={2}
            />
            <Bar
              dataKey="upfrontFees"
              stackId="cost"
              fill="var(--color-upfrontFees)"
              stroke="var(--background)"
              strokeWidth={2}
            />
            {hasPmi ? (
              <Bar dataKey="pmi" stackId="cost" fill="var(--color-pmi)" stroke="var(--background)" strokeWidth={2} />
            ) : null}
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
