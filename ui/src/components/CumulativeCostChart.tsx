import { CartesianGrid, Line, LineChart, ReferenceLine, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartLegendContent, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { ChartLegend, ChartTooltip } from "@/components/ui/chart-primitives";
import { chartLabel, offerLabel, SERIES_COLORS } from "@/lib/comparison-presentation";
import { formatCompactCurrency, formatCurrency, formatMonths } from "@/lib/formatters";
import type { PlanComparison } from "@/lib/types";

type Row = { month: number } & Record<string, number>;

export function cumulativeCostRows(comparison: PlanComparison): Row[] {
  const length = Math.max(...comparison.plans.map((plan) => plan.cumulative_cost.length));
  const step = length > 120 ? 3 : 1;
  const rows: Row[] = [];
  for (let month = 0; month < length; month += 1) {
    if (month % step !== 0 && month !== length - 1) continue;
    const row: Row = { month };
    comparison.plans.forEach((plan, index) => {
      const series = plan.cumulative_cost;
      row[`plan${index}`] = Number(series[Math.min(month, series.length - 1)]);
    });
    rows.push(row);
  }
  return rows;
}

interface EndLabelProps {
  x?: string | number;
  y?: string | number;
  index?: number;
}

export function CumulativeCostChart({ comparison, currency }: { comparison: PlanComparison; currency: string }) {
  const rows = cumulativeCostRows(comparison);
  const config = Object.fromEntries(
    comparison.plans.map((plan, index) => [`plan${index}`, { label: chartLabel(plan), color: SERIES_COLORS[index] }]),
  ) satisfies ChartConfig;
  const lastIndex = rows.length - 1;
  const years = (month: number) => (month % 12 === 0 ? `${month / 12}y` : "");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost over time</CardTitle>
        <CardDescription>
          Upfront fees, interest, prepayment fees, and PMI paid so far. Where lines cross, the cheaper offer changes:
          lower fees win short stays, lower rates win long ones.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={config} className="h-80 w-full">
          <LineChart accessibilityLayer data={rows} margin={{ top: 12, right: 104, bottom: 4, left: 4 }}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="month"
              type="number"
              domain={[0, "dataMax"]}
              ticks={rows.filter((row) => row.month % 60 === 0).map((row) => row.month)}
              tickFormatter={years}
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
                  labelFormatter={(_, payload) => {
                    const month = Number(payload?.[0]?.payload?.month ?? 0);
                    return month === 0 ? "At signing" : `After ${formatMonths(month)}`;
                  }}
                  formatter={(value, name) => (
                    <div className="flex w-full items-center justify-between gap-4">
                      <span>{config[name as keyof typeof config]?.label ?? name}</span>
                      <span className="font-mono tabular-nums">{formatCurrency(Number(value), currency)}</span>
                    </div>
                  )}
                />
              }
            />
            <ChartLegend content={<ChartLegendContent />} />
            {comparison.horizon_months !== null ? (
              <ReferenceLine
                x={comparison.horizon_months}
                stroke="var(--muted-foreground)"
                strokeDasharray="4 4"
                label={{
                  value: formatMonths(comparison.horizon_months),
                  position: "insideTopRight",
                  fill: "var(--muted-foreground)",
                  fontSize: 11,
                }}
              />
            ) : null}
            {comparison.plans.map((plan, index) => (
              <Line
                key={plan.id}
                dataKey={`plan${index}`}
                type="monotone"
                stroke={`var(--color-plan${index})`}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--background)" }}
                isAnimationActive={false}
                label={({ x, y, index: point }: EndLabelProps) =>
                  point === lastIndex && x !== undefined && y !== undefined ? (
                    <text x={Number(x) + 6} y={y} dy={4} fontSize={11} fill="var(--foreground)">
                      {offerLabel(plan).slice(0, 14)}
                    </text>
                  ) : (
                    <g />
                  )
                }
              />
            ))}
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
