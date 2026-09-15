import { useQuery } from "@tanstack/react-query";
import { getRouteApi, Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeftIcon, CircleAlertIcon } from "lucide-react";
import { PlanComparisonSummary } from "@/components/PlanComparisonSummary";
import { PlanComparisonTable } from "@/components/PlanComparisonTable";
import { PlanCostChart } from "@/components/PlanCostChart";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency } from "@/lib/formatters";
import { parsePlanIds } from "@/lib/plan-selection";
import { plansApi } from "@/lib/plans-api";

const route = getRouteApi("/_app/compare");

export function ComparePage() {
  const search = route.useSearch();
  const navigate = useNavigate();
  const planIds = parsePlanIds(search.plans);
  const query = useQuery({
    queryKey: ["plan-comparison", planIds],
    queryFn: () => plansApi.previewComparison(planIds),
    retry: false,
  });
  const changePlans = () => navigate({ to: "/", search: { compare: planIds.join(",") } });
  const comparison = query.data;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
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
        <Button variant="outline" onClick={changePlans}>
          Change plans
        </Button>
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
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {comparison.plans.map((plan) => (
              <Card key={plan.id}>
                <CardHeader>
                  <CardTitle>
                    <Link to="/plans/$planId" params={{ planId: plan.id }} className="underline underline-offset-4">
                      {plan.lender || plan.name}
                    </Link>
                  </CardTitle>
                  {plan.lender && <CardDescription>{plan.name}</CardDescription>}
                </CardHeader>
                <CardContent>
                  <dl className="flex flex-col gap-4">
                    {(["starting_monthly_payment", "total_cost"] as const).map((metric) => (
                      <div key={metric}>
                        <dt className="text-sm text-muted-foreground">
                          {metric === "total_cost" ? "Total cost" : "Starting monthly payment"}
                        </dt>
                        <dd className="flex flex-wrap items-center gap-2 text-lg font-semibold tabular-nums">
                          {formatCurrency(plan[metric])}
                          {comparison.best_plan_ids_by_metric[metric]?.includes(plan.id) && (
                            <Badge variant="secondary">Best</Badge>
                          )}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </CardContent>
              </Card>
            ))}
          </div>
          <PlanCostChart comparison={comparison} />
          <PlanComparisonTable comparison={comparison} />
        </>
      ) : null}
    </div>
  );
}
