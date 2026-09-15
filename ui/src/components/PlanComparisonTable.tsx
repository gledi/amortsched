import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCurrency, formatDate, formatPercent, formatTerm } from "@/lib/formatters";
import type { PlanComparison, PlanComparisonItem } from "@/lib/types";
import { cn } from "@/lib/utils";

const metrics: { key: string; label: string; value: (plan: PlanComparisonItem) => string }[] = [
  {
    key: "starting_monthly_payment",
    label: "Starting monthly payment",
    value: (p) => formatCurrency(p.starting_monthly_payment),
  },
  { key: "total_cost", label: "Total cost", value: (p) => formatCurrency(p.total_cost) },
  { key: "lender", label: "Lender", value: (p) => p.lender || "—" },
  { key: "name", label: "Plan name", value: (p) => p.name },
  { key: "principal", label: "Principal", value: (p) => formatCurrency(p.principal) },
  { key: "interest_rate", label: "Interest rate", value: (p) => formatPercent(p.interest_rate) },
  { key: "term", label: "Term", value: (p) => formatTerm(p.term) },
  { key: "start_date", label: "Start date", value: (p) => formatDate(p.start_date) },
  { key: "upfront_fees", label: "Upfront fees", value: (p) => formatCurrency(p.upfront_fees) },
  {
    key: "early_payment_fixed",
    label: "Early-payment fee (fixed)",
    value: (p) => formatCurrency(p.configured_early_payment_fees.fixed),
  },
  {
    key: "early_payment_percent",
    label: "Early-payment fee (%)",
    value: (p) => formatPercent(p.configured_early_payment_fees.percent),
  },
  { key: "total_principal", label: "Schedule principal", value: (p) => formatCurrency(p.total_principal) },
  { key: "total_interest", label: "Schedule interest", value: (p) => formatCurrency(p.total_interest) },
  { key: "schedule_fees", label: "Schedule fees", value: (p) => formatCurrency(p.schedule_fees) },
  { key: "schedule_total_outflow", label: "Schedule outflow", value: (p) => formatCurrency(p.schedule_total_outflow) },
  { key: "payoff_months", label: "Months to payoff", value: (p) => String(p.payoff_months) },
  { key: "payoff_month", label: "Payoff month", value: (p) => formatDate(p.payoff_month) },
  { key: "paid_off", label: "Paid off", value: (p) => (p.paid_off ? "Yes" : "No") },
  {
    key: "one_time_extra_payments",
    label: "One-time extra payments",
    value: (p) => String(p.adjustment_counts.one_time_extra_payments),
  },
  {
    key: "recurring_extra_payments",
    label: "Recurring extra payments",
    value: (p) => String(p.adjustment_counts.recurring_extra_payments),
  },
  {
    key: "interest_rate_changes",
    label: "Interest rate changes",
    value: (p) => String(p.adjustment_counts.interest_rate_changes),
  },
];

export function PlanComparisonTable({ comparison }: { comparison: PlanComparison }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Offer details</CardTitle>
        <CardDescription>Compare terms, costs, and payoff timing. Best values include ties.</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableCaption>Loan offer comparison. Scroll horizontally to see all selected plans.</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead scope="col" className="sticky left-0 z-10 min-w-40 bg-card">
                Metric
              </TableHead>
              {comparison.plans.map((plan) => (
                <TableHead key={plan.id} scope="col" className="min-w-44">
                  <Link to="/plans/$planId" params={{ planId: plan.id }} className="underline underline-offset-4">
                    {plan.lender || plan.name}
                  </Link>
                  {plan.lender && <div className="mt-1 text-muted-foreground">{plan.name}</div>}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {metrics.map((metric) => (
              <TableRow key={metric.key}>
                <TableHead scope="row" className="sticky left-0 z-10 bg-card">
                  {metric.label}
                </TableHead>
                {comparison.plans.map((plan) => {
                  const best = comparison.best_plan_ids_by_metric[metric.key]?.includes(plan.id) ?? false;
                  return (
                    <TableCell key={plan.id} className={cn(best && "bg-primary/5")}>
                      <div className="flex items-center gap-2">
                        {metric.value(plan)}
                        {best && <Badge variant="secondary">Best</Badge>}
                      </div>
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
