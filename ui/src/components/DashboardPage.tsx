import * as React from "react";
import { getRouteApi, Link, useRouter } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { plansApi } from "@/lib/plans-api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CreatePlanDialog } from "@/components/CreatePlanDialog";
import { PlanSelectionBar } from "@/components/PlanSelectionBar";
import { formatCurrency, formatPercent, formatTerm, formatDate } from "@/lib/formatters";
import { loanTypeLabel } from "@/lib/plan-form";
import type { Plan } from "@/lib/types";
import { isComparableSelection, restorePlanSelection, togglePlanSelection } from "@/lib/plan-selection";
import {
  LayersIcon,
  DollarSignIcon,
  BookmarkCheckIcon,
  FileTextIcon,
  Trash2Icon,
  ArrowRightIcon,
  CalendarIcon,
  ClockIcon,
  TrendingUpIcon,
  PercentIcon,
  WalletIcon,
} from "lucide-react";

export function principalByCurrency(plans: Plan[]): string {
  const totals = new Map<string, number>();
  for (const plan of plans) {
    const amount = Number(plan.amount);
    if (Number.isFinite(amount)) totals.set(plan.currency, (totals.get(plan.currency) ?? 0) + amount);
  }
  if (totals.size === 0) return formatCurrency(0);
  return [...totals.entries()].map(([currency, total]) => formatCurrency(total, currency)).join(" · ");
}

function monthlyTotal(plan: Plan): number {
  return Number(plan.monthly_payment) + (plan.monthly_housing ? Number(plan.monthly_housing.total) : 0);
}

const route = getRouteApi("/_app/");

export function DashboardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const search = route.useSearch();
  const selectionMode = typeof search.compare === "string";
  const [limitSelection, setLimitSelection] = React.useState<string | null>(null);

  const {
    data: plans = [],
    isLoading,
    isSuccess,
  } = useQuery({
    queryKey: ["plans"],
    queryFn: plansApi.listPlans,
  });
  const selection = restorePlanSelection(search.compare, isSuccess ? plans.map((plan) => plan.id) : []);
  const selectedIds = selection.ids;
  const limitReached = limitSelection === search.compare;

  const deleteMutation = useMutation({
    mutationFn: plansApi.deletePlan,
    onSuccess: (_, planId) => {
      queryClient.setQueryData<Plan[]>(["plans"], (prev = []) => prev.filter((p) => p.id !== planId));
    },
  });

  function handlePlanCreated(newPlan: Plan) {
    queryClient.setQueryData<Plan[]>(["plans"], (prev = []) => [newPlan, ...prev]);
    router.navigate({
      to: "/plans/$planId",
      params: { planId: newPlan.id },
    });
  }

  function startSelection() {
    router.navigate({ to: "/", search: { compare: "" } });
  }

  function toggleSelection(planId: string) {
    const nextSelection = togglePlanSelection(selectedIds, planId);
    setLimitSelection(nextSelection.limitReached ? nextSelection.ids.join(",") : null);
    router.navigate({ to: "/", search: { compare: nextSelection.ids.join(",") } });
  }

  function cancelSelection() {
    setLimitSelection(null);
    router.navigate({ to: "/", search: { compare: undefined } });
  }

  function compareSelectedPlans() {
    if (!isSuccess || !isComparableSelection(selectedIds)) return;
    router.navigate({ to: "/compare", search: { plans: selectedIds.join(",") } });
  }

  const savedCount = plans.filter((p) => p.status === "saved").length;
  const draftCount = plans.filter((p) => p.status === "draft").length;

  return (
    <div className="mx-auto max-w-7xl flex flex-col gap-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Loan Plans</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Every offer you&apos;re weighing, with its true monthly cost. Select two to four to compare them.
          </p>
        </div>
        {selectionMode ? null : (
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={startSelection}>
              Compare plans
            </Button>
            <CreatePlanDialog onPlanCreated={handlePlanCreated} />
          </div>
        )}
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card size="sm">
          <CardHeader className="pb-1">
            <CardDescription className="flex items-center gap-1">
              <FileTextIcon className="size-3" />
              Total Plans
            </CardDescription>
            <CardTitle className="text-xl font-bold">{plans.length}</CardTitle>
          </CardHeader>
        </Card>

        <Card size="sm">
          <CardHeader className="pb-1">
            <CardDescription className="flex items-center gap-1">
              <BookmarkCheckIcon className="size-3" />
              Saved Plans
            </CardDescription>
            <CardTitle className="text-xl font-bold text-emerald-600">{savedCount}</CardTitle>
          </CardHeader>
        </Card>

        <Card size="sm">
          <CardHeader className="pb-1">
            <CardDescription className="flex items-center gap-1">
              <LayersIcon className="size-3" />
              Draft Plans
            </CardDescription>
            <CardTitle className="text-xl font-bold text-muted-foreground">{draftCount}</CardTitle>
          </CardHeader>
        </Card>

        <Card size="sm">
          <CardHeader className="pb-1">
            <CardDescription className="flex items-center gap-1">
              <DollarSignIcon className="size-3" />
              Total principal
            </CardDescription>
            <CardTitle className="text-xl font-bold text-primary">{principalByCurrency(plans)}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Plans List or Empty State */}
      {isLoading ? (
        <div className="flex min-h-[300px] items-center justify-center">
          <p className="text-xs text-muted-foreground animate-pulse">Loading loan plans...</p>
        </div>
      ) : plans.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="rounded-full bg-muted p-4 mb-4">
              <LayersIcon className="size-8 text-muted-foreground" />
            </div>
            <h3 className="text-base font-semibold">No Loan Plans Yet</h3>
            <p className="mt-1 text-xs text-muted-foreground max-w-sm">
              Add a mortgage or loan offer to see its monthly cost, full payment schedule, and what extra payments or a
              refinance would save you.
            </p>
            <div className="mt-6">
              <CreatePlanDialog onPlanCreated={handlePlanCreated} />
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {plans.map((plan) => {
            const isDraft = plan.status === "draft";
            const adjustmentsCount =
              (plan.one_time_extra_payments?.length || 0) +
              (plan.recurring_extra_payments?.length || 0) +
              (plan.interest_rate_changes?.length || 0);

            return (
              <Card
                key={plan.id}
                className="flex flex-col justify-between hover:shadow-xs transition-shadow"
                role={selectionMode ? "checkbox" : undefined}
                aria-checked={selectionMode ? selectedIds.includes(plan.id) : undefined}
                tabIndex={selectionMode ? 0 : undefined}
                onClick={selectionMode ? () => toggleSelection(plan.id) : undefined}
                onKeyDown={
                  selectionMode
                    ? (event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          toggleSelection(plan.id);
                        }
                      }
                    : undefined
                }
              >
                <CardHeader>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <CardTitle className="text-base font-semibold">
                        {selectionMode ? (
                          plan.lender || plan.name
                        ) : (
                          <Link to="/plans/$planId" params={{ planId: plan.id }} className="hover:underline">
                            {plan.lender || plan.name}
                          </Link>
                        )}
                      </CardTitle>
                      {plan.lender ? <CardDescription>{plan.name}</CardDescription> : null}
                      <CardDescription className="mt-0.5 text-[11px]">
                        {loanTypeLabel(plan.loan_type)} · {plan.currency}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      {selectionMode ? (
                        <Checkbox
                          checked={selectedIds.includes(plan.id)}
                          aria-hidden="true"
                          tabIndex={-1}
                          className="pointer-events-none"
                        />
                      ) : null}
                      <Badge variant={isDraft ? "outline" : "default"}>{isDraft ? "Draft" : "Saved"}</Badge>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="flex flex-col gap-3">
                  <div className="flex items-baseline justify-between border-b border-border/50 pb-2">
                    <span className="text-xs text-muted-foreground">Loan amount</span>
                    <span className="font-mono text-lg font-bold text-primary">
                      {formatCurrency(plan.amount, plan.currency)}
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between text-xs">
                    <span className="flex items-center gap-1 text-muted-foreground">
                      <WalletIcon className="size-3" /> Monthly
                    </span>
                    <span className="font-mono font-semibold">{formatCurrency(monthlyTotal(plan), plan.currency)}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <PercentIcon className="size-3" /> Rate
                      </span>
                      <span className="font-semibold">{formatPercent(plan.interest_rate)}</span>
                    </div>

                    <div className="flex flex-col gap-0.5">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <ClockIcon className="size-3" /> Term
                      </span>
                      <span className="font-semibold">{formatTerm(plan.term)}</span>
                    </div>

                    <div className="flex flex-col gap-0.5">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <CalendarIcon className="size-3" /> Starts
                      </span>
                      <span className="font-semibold">{formatDate(plan.start_date)}</span>
                    </div>

                    <div className="flex flex-col gap-0.5">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <TrendingUpIcon className="size-3" /> Adjustments
                      </span>
                      <span className="font-semibold">
                        {adjustmentsCount > 0 ? `${adjustmentsCount} active` : "None"}
                      </span>
                    </div>
                  </div>
                </CardContent>

                {selectionMode ? null : (
                  <CardFooter className="flex items-center justify-between border-t border-border pt-3">
                    <ConfirmDialog
                      title={`Delete "${plan.name}"?`}
                      description="The plan and all of its schedules are removed. This cannot be undone."
                      confirmLabel="Delete plan"
                      onConfirm={() => deleteMutation.mutateAsync(plan.id)}
                      trigger={
                        <Button variant="ghost" size="sm" className="px-2 text-destructive hover:text-destructive">
                          <Trash2Icon data-icon="inline-start" />
                          Delete
                        </Button>
                      }
                    />

                    <Link to="/plans/$planId" params={{ planId: plan.id }}>
                      <Button size="sm">
                        Open
                        <ArrowRightIcon data-icon="inline-end" />
                      </Button>
                    </Link>
                  </CardFooter>
                )}
              </Card>
            );
          })}
        </div>
      )}
      {selectionMode ? (
        <PlanSelectionBar
          selectedCount={selectedIds.length}
          limitReached={limitReached}
          removedCount={isSuccess ? selection.removedCount : 0}
          onCancel={cancelSelection}
          onCompare={compareSelectedPlans}
        />
      ) : null}
    </div>
  );
}
