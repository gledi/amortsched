import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCurrency, formatDate, formatMonths, formatPercent, formatTerm } from "@/lib/formatters";
import { loanTypeLabel } from "@/lib/plan-form";
import type { PlanComparison, PlanComparisonItem } from "@/lib/types";
import { cn } from "@/lib/utils";

type Metric = { key: string; label: string; value: (plan: PlanComparisonItem) => string };

const money = (plan: PlanComparisonItem, value: string | number | null) =>
  value === null ? "—" : formatCurrency(value, plan.currency);

const headlineMetrics: Metric[] = [
  {
    key: "starting_total_monthly_payment",
    label: "Monthly payment (incl. tax, insurance, PMI)",
    value: (p) => money(p, p.starting_total_monthly_payment),
  },
  { key: "starting_monthly_payment", label: "Loan payment", value: (p) => money(p, p.starting_monthly_payment) },
  { key: "total_cost", label: "Total cost", value: (p) => money(p, p.total_cost) },
];

const detailMetrics: Metric[] = [
  { key: "lender", label: "Lender", value: (p) => p.lender || "—" },
  { key: "name", label: "Plan name", value: (p) => p.name },
  { key: "loan_type", label: "Loan type", value: (p) => loanTypeLabel(p.loan_type) },
  { key: "currency", label: "Currency", value: (p) => p.currency },
  { key: "principal", label: "Loan amount", value: (p) => money(p, p.principal) },
  { key: "down_payment", label: "Down payment", value: (p) => money(p, p.down_payment) },
  { key: "ltv", label: "Loan-to-value", value: (p) => (p.ltv === null ? "—" : formatPercent(p.ltv)) },
  { key: "interest_rate", label: "Interest rate", value: (p) => formatPercent(p.interest_rate) },
  { key: "term", label: "Term", value: (p) => formatTerm(p.term) },
  { key: "start_date", label: "First payment", value: (p) => formatDate(p.start_date) },
  {
    key: "starting_monthly_housing",
    label: "Tax, insurance, HOA & PMI / month",
    value: (p) => money(p, p.starting_monthly_housing),
  },
  { key: "upfront_fees", label: "Upfront fees", value: (p) => money(p, p.upfront_fees) },
  {
    key: "early_payment_fixed",
    label: "Prepayment fee (fixed)",
    value: (p) => money(p, p.configured_early_payment_fees.fixed),
  },
  {
    key: "early_payment_percent",
    label: "Prepayment fee (%)",
    value: (p) => formatPercent(p.configured_early_payment_fees.percent),
  },
  { key: "total_interest", label: "Total interest", value: (p) => money(p, p.total_interest) },
  { key: "schedule_fees", label: "Prepayment fees paid", value: (p) => money(p, p.schedule_fees) },
  { key: "total_pmi", label: "Total PMI", value: (p) => money(p, p.total_pmi) },
  { key: "total_escrow", label: "Tax, insurance & HOA (not loan cost)", value: (p) => money(p, p.total_escrow) },
  { key: "payoff_months", label: "Months to payoff", value: (p) => String(p.payoff_months) },
  { key: "payoff_month", label: "Payoff month", value: (p) => formatDate(p.payoff_month) },
  { key: "paid_off", label: "Paid off", value: (p) => (p.paid_off ? "Yes" : "No") },
  {
    key: "adjustments",
    label: "Extra payments / rate changes",
    value: (p) =>
      `${p.adjustment_counts.one_time_extra_payments + p.adjustment_counts.recurring_extra_payments} / ${p.adjustment_counts.interest_rate_changes}`,
  },
];

function horizonMetrics(months: number): Metric[] {
  const period = formatMonths(months);
  return [
    {
      key: "cost_at_horizon",
      label: `Cost if you exit after ${period}`,
      value: (p) => (p.horizon ? money(p, p.horizon.cost) : "—"),
    },
    {
      key: "balance_at_horizon",
      label: `Balance left after ${period}`,
      value: (p) => (p.horizon ? money(p, p.horizon.balance) : "—"),
    },
  ];
}

export function PlanComparisonTable({ comparison }: { comparison: PlanComparison }) {
  const metrics = [
    ...headlineMetrics,
    ...(comparison.horizon_months !== null ? horizonMetrics(comparison.horizon_months) : []),
    ...detailMetrics,
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Offer details</CardTitle>
        <CardDescription>
          Total cost is everything paid to the lender plus upfront fees and PMI. Best values include ties.
        </CardDescription>
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
