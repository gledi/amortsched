import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartLegendContent, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { ChartLegend, ChartTooltip } from "@/components/ui/chart-primitives";
import { formatCurrency } from "@/lib/formatters";
import type { PlanComparison } from "@/lib/types";

const chartConfig = {
  scheduleOutflow: { label: "Schedule outflow", color: "var(--chart-1)" },
  upfrontFees: { label: "Upfront fees", color: "var(--chart-2)" },
} satisfies ChartConfig;

export function PlanCostChart({ comparison }: { comparison: PlanComparison }) {
  const data = comparison.plans.map((plan) => ({
    label: plan.lender ? `${plan.lender} — ${plan.name}` : plan.name,
    scheduleOutflow: Number(plan.schedule_total_outflow),
    upfrontFees: Number(plan.upfront_fees),
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Total cost by offer</CardTitle>
        <CardDescription>Each bar stacks schedule outflow and upfront fees to show the full cost.</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-80 w-full">
          <BarChart accessibilityLayer data={data} margin={{ top: 12, right: 12, bottom: 12, left: 12 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} interval={0} height={60} />
            <YAxis tickLine={false} axisLine={false} width={90} tickFormatter={(value) => formatCurrency(value)} />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  formatter={(value, name) => (
                    <div className="flex w-full items-center justify-between gap-4">
                      <span>{chartConfig[name as keyof typeof chartConfig]?.label ?? name}</span>
                      <span className="font-mono tabular-nums">{formatCurrency(Number(value))}</span>
                    </div>
                  )}
                />
              }
            />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar dataKey="scheduleOutflow" stackId="total-cost" fill="var(--color-scheduleOutflow)" />
            <Bar dataKey="upfrontFees" stackId="total-cost" fill="var(--color-upfrontFees)" />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
