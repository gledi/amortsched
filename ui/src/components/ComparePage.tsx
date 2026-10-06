import { useQuery } from "@tanstack/react-query";
import { getRouteApi, Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeftIcon, CircleAlertIcon, HourglassIcon } from "lucide-react";
import { CumulativeCostChart } from "@/components/CumulativeCostChart";
import { PlanComparisonSummary } from "@/components/PlanComparisonSummary";
import { PlanComparisonTable } from "@/components/PlanComparisonTable";
import { PlanCostChart } from "@/components/PlanCostChart";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { comparisonCurrency, horizonHeadline, offerLabel } from "@/lib/comparison-presentation";
import { formatCurrency } from "@/lib/formatters";
import { parsePlanIds } from "@/lib/plan-selection";
import { plansApi } from "@/lib/plans-api";
import type { PlanComparison, PlanComparisonItem } from "@/lib/types";

const route = getRouteApi("/_app/compare");

const HORIZON_OPTIONS = [3, 5, 7, 10, 15, 20] as const;

function OfferCard({ comparison, plan }: { comparison: PlanComparison; plan: PlanComparisonItem }) {
  const best = (metric: string) => comparison.best_plan_ids_by_metric[metric]?.includes(plan.id) ?? false;
  const rows: { metric: string; label: string; value: string | number }[] = [
    { metric: "starting_total_monthly_payment", label: "Monthly payment", value: plan.starting_total_monthly_payment },
    { metric: "total_cost", label: "Total cost", value: plan.total_cost },
  ];
  if (plan.horizon) {
    rows.push({ metric: "cost_at_horizon", label: "Cost if you exit early", value: plan.horizon.cost });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Link to="/plans/$planId" params={{ planId: plan.id }} className="underline underline-offset-4">
            {offerLabel(plan)}
          </Link>
        </CardTitle>
        {plan.lender ? <CardDescription>{plan.name}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        <dl className="flex flex-col gap-4">
          {rows.map((row) => (
            <div key={row.metric}>
              <dt className="text-sm text-muted-foreground">{row.label}</dt>
              <dd className="flex flex-wrap items-center gap-2 text-lg font-semibold tabular-nums">
                {formatCurrency(row.value, plan.currency)}
                {best(row.metric) ? <Badge variant="secondary">Best</Badge> : null}
              </dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

export function ComparePage() {
  const search = route.useSearch();
  const navigate = useNavigate();
  const planIds = parsePlanIds(search.plans);
  const horizonMonths = search.horizon ? search.horizon * 12 : undefined;
  const query = useQuery({
    queryKey: ["plan-comparison", planIds, horizonMonths ?? null],
    queryFn: () => plansApi.previewComparison(planIds, horizonMonths),
    retry: false,
    placeholderData: (previous) => previous,
  });
  const changePlans = () => navigate({ to: "/", search: { compare: planIds.join(",") } });
  const setHorizon = (value: string) =>
    navigate({
      to: "/compare",
      search: { plans: search.plans, horizon: value === "full" ? undefined : Number(value) },
      replace: true,
    });
  const comparison = query.data;
  const currency = comparison ? comparisonCurrency(comparison) : null;
  const horizonNote = comparison ? horizonHeadline(comparison) : null;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-2">
          <Link
            to="/"
            search={{ compare: undefined }}
            className="flex items-center gap-2 text-sm text-muted-foreground"
          >
            <ArrowLeftIcon className="size-4" /> Back to plans
          </Link>
          <h1 className="text-2xl font-semibold">Compare {planIds.length} loan offers</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">How long will you keep the loan?</span>
          <Select value={search.horizon ? String(search.horizon) : "full"} onValueChange={(v) => v && setHorizon(v)}>
            <SelectTrigger className="w-36" aria-label="How long will you keep the loan?">
              <SelectValue>{search.horizon ? `${search.horizon} years` : "Full term"}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="full">Full term</SelectItem>
                {HORIZON_OPTIONS.map((years) => (
                  <SelectItem key={years} value={String(years)}>
                    {years} years
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={changePlans}>
            Change plans
          </Button>
        </div>
      </div>

      {query.isLoading ? (
        <div role="status" aria-label="Loading comparison" className="flex flex-col gap-6">
          <span className="sr-only">Loading comparison…</span>
          <Skeleton className="h-20 w-full" />
          <div className="grid gap-4 sm:grid-cols-2">
            {planIds.map((id) => (
              <Skeleton key={id} className="h-36 w-full" />
            ))}
          </div>
          <Skeleton className="h-80 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      ) : query.isError ? (
        <Alert variant="destructive">
          <CircleAlertIcon />
          <AlertTitle>Could not compare these plans</AlertTitle>
          <AlertDescription>
            <p>{query.error.message || "Something went wrong while generating this comparison."}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button onClick={() => void query.refetch()} disabled={query.isFetching}>
                {query.isFetching ? "Retrying…" : "Retry"}
              </Button>
              <Button variant="outline" onClick={changePlans}>
                Change plans
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      ) : comparison ? (
        <>
          <PlanComparisonSummary comparison={comparison} />
          {horizonNote ? (
            <Alert variant="info">
              <HourglassIcon />
              <AlertTitle>{horizonNote}</AlertTitle>
              <AlertDescription>
                Counts upfront fees, interest, PMI, and any prepayment penalty when you pay off the remaining balance.
              </AlertDescription>
            </Alert>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {comparison.plans.map((plan) => (
              <OfferCard key={plan.id} comparison={comparison} plan={plan} />
            ))}
          </div>
          {currency ? (
            <>
              <CumulativeCostChart comparison={comparison} currency={currency} />
              <PlanCostChart comparison={comparison} currency={currency} />
            </>
          ) : (
            <Alert>
              <CircleAlertIcon />
              <AlertTitle>Charts are hidden for offers in different currencies</AlertTitle>
              <AlertDescription>Each offer is shown in its own currency in the table below.</AlertDescription>
            </Alert>
          )}
          <PlanComparisonTable comparison={comparison} />
        </>
      ) : null}
    </div>
  );
}
