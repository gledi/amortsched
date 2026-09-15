import * as React from "react";
import { useState } from "react";
import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { plansApi } from "@/lib/plans-api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ScheduleView } from "@/components/ScheduleView";
import { AdjustmentsView } from "@/components/AdjustmentsView";
import { EditPlanDialog } from "@/components/EditPlanDialog";
import {
  formatCurrency,
  formatPercent,
  formatTerm,
  formatDate,
} from "@/lib/formatters";
import type { Plan, Schedule } from "@/lib/types";
import {
  ArrowLeftIcon,
  PlayIcon,
  BookmarkCheckIcon,
  Trash2Icon,
  CalendarIcon,
  DollarSignIcon,
  PercentIcon,
  ClockIcon,
  CheckIcon,
  LayersIcon,
  SlidersHorizontalIcon,
} from "lucide-react";

export const Route = createFileRoute("/_app/plans/$planId")({
  component: PlanDetailPage,
});

function PlanDetailPage() {
  const { planId } = Route.useParams();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<string>("schedule");
  const [activeScheduleId, setActiveScheduleId] = useState<string | null>(null);

  // Fetch plan details
  const {
    data: plan,
    isLoading: isPlanLoading,
    error: planError,
  } = useQuery({
    queryKey: ["plan", planId],
    queryFn: () => plansApi.getPlan(planId),
  });

  // Fetch schedules for plan
  const {
    data: schedules = [],
    isLoading: isSchedulesLoading,
    refetch: refetchSchedules,
  } = useQuery({
    queryKey: ["schedules", planId],
    queryFn: () => plansApi.listSchedules(planId),
  });

  // Generate schedule mutation
  const generateMutation = useMutation({
    mutationFn: () => plansApi.generateSchedule(planId),
    onSuccess: (newSchedule) => {
      queryClient.setQueryData<Schedule[]>(["schedules", planId], (prev = []) => [
        newSchedule,
        ...prev.filter((s) => s.id !== newSchedule.id),
      ]);
      setActiveScheduleId(newSchedule.id);
      setActiveTab("schedule");
    },
    onError: (err: any) => {
      alert(err?.message || "Failed to generate amortization schedule");
    },
  });

  // Save plan mutation
  const savePlanMutation = useMutation({
    mutationFn: () => plansApi.savePlan(planId),
    onSuccess: (updatedPlan) => {
      queryClient.setQueryData(["plan", planId], updatedPlan);
      queryClient.invalidateQueries({ queryKey: ["plans"] });
    },
    onError: (err: any) => {
      alert(err?.message || "Failed to promote plan to saved");
    },
  });

  // Delete plan mutation
  const deletePlanMutation = useMutation({
    mutationFn: () => plansApi.deletePlan(planId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      router.navigate({ to: "/" });
    },
    onError: (err: any) => {
      alert(err?.message || "Failed to delete plan");
    },
  });

  if (isPlanLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <p className="text-xs text-muted-foreground animate-pulse">Loading loan plan details...</p>
      </div>
    );
  }

  if (planError || !plan) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <p className="text-sm font-semibold text-destructive">Failed to load plan</p>
        <p className="text-xs text-muted-foreground">The plan may not exist or has been removed.</p>
        <Link to="/">
          <Button variant="outline" size="sm">
            <ArrowLeftIcon data-icon="inline-start" />
            Back to Dashboard
          </Button>
        </Link>
      </div>
    );
  }

  const isDraft = plan.status === "draft";
  const adjustmentsCount =
    (plan.one_time_extra_payments?.length || 0) +
    (plan.recurring_extra_payments?.length || 0) +
    (plan.interest_rate_changes?.length || 0);

  function handlePlanUpdated(updatedPlan: Plan) {
    queryClient.setQueryData(["plan", planId], updatedPlan);
    queryClient.invalidateQueries({ queryKey: ["plans"] });
  }

  function handleScheduleDeleted(deletedId: string) {
    queryClient.setQueryData<Schedule[]>(["schedules", planId], (prev = []) =>
      prev.filter((s) => s.id !== deletedId)
    );
    if (activeScheduleId === deletedId) {
      setActiveScheduleId(null);
    }
  }

  function handleScheduleSaved(savedSchedule: Schedule) {
    queryClient.setQueryData<Schedule[]>(["schedules", planId], (prev = []) =>
      prev.map((s) => (s.id === savedSchedule.id ? savedSchedule : s))
    );
  }

  return (
    <div className="mx-auto max-w-7xl flex flex-col gap-6">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <Link
              to="/"
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
            >
              <ArrowLeftIcon className="size-3" />
              Plans
            </Link>
            <span className="text-muted-foreground">/</span>
            <span className="text-xs font-mono text-muted-foreground">{plan.slug}</span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{plan.name}</h1>
            <Badge variant={isDraft ? "outline" : "default"}>
              {isDraft ? "Draft" : "Saved"}
            </Badge>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
          >
            <PlayIcon data-icon="inline-start" />
            {generateMutation.isPending ? "Calculating..." : "Generate Schedule"}
          </Button>

          {isDraft && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => savePlanMutation.mutate()}
              disabled={savePlanMutation.isPending}
            >
              <BookmarkCheckIcon data-icon="inline-start" />
              {savePlanMutation.isPending ? "Saving..." : "Save Plan"}
            </Button>
          )}

          <EditPlanDialog plan={plan} onPlanUpdated={handlePlanUpdated} />

          <Button
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive"
            onClick={() => {
              if (confirm(`Are you sure you want to delete "${plan.name}"?`)) {
                deletePlanMutation.mutate();
              }
            }}
            disabled={deletePlanMutation.isPending}
          >
            <Trash2Icon data-icon="inline-start" />
            Delete
          </Button>
        </div>
      </div>

      {/* Plan Parameters Overview Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card size="sm">
          <CardHeader className="pb-1">
            <CardDescription className="flex items-center gap-1">
              <DollarSignIcon className="size-3" />
              Loan Amount
            </CardDescription>
            <CardTitle className="text-base font-bold text-primary">
              {formatCurrency(plan.amount)}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card size="sm">
          <CardHeader className="pb-1">
            <CardDescription className="flex items-center gap-1">
              <PercentIcon className="size-3" />
              Interest Rate
            </CardDescription>
            <CardTitle className="text-base font-bold">
              {formatPercent(plan.interest_rate)}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card size="sm">
          <CardHeader className="pb-1">
            <CardDescription className="flex items-center gap-1">
              <ClockIcon className="size-3" />
              Term Length
            </CardDescription>
            <CardTitle className="text-base font-bold">
              {formatTerm(plan.term)}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card size="sm">
          <CardHeader className="pb-1">
            <CardDescription className="flex items-center gap-1">
              <CalendarIcon className="size-3" />
              Start Date
            </CardDescription>
            <CardTitle className="text-sm font-semibold">
              {formatDate(plan.start_date)}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card size="sm">
          <CardHeader className="pb-1">
            <CardDescription>Early Payoff Fees</CardDescription>
            <CardTitle className="text-xs font-semibold truncate">
              {formatCurrency(plan.early_payment_fees?.fixed ?? 0)} + {formatPercent(plan.early_payment_fees?.percent ?? 0)}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card size="sm">
          <CardHeader className="pb-1">
            <CardDescription>Proration Rule</CardDescription>
            <CardTitle className="text-xs font-semibold capitalize truncate">
              {plan.interest_rate_application?.replace(/_/g, " ") || "Whole Month"}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={(val) => val && setActiveTab(val)}>
        <TabsList>
          <TabsTrigger value="schedule" className="gap-2">
            <LayersIcon className="size-3.5" />
            Amortization Schedule
            {schedules.length > 0 && (
              <Badge variant="secondary" className="px-1.5 py-0 h-4 text-[10px]">
                {schedules.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="adjustments" className="gap-2">
            <SlidersHorizontalIcon className="size-3.5" />
            Adjustments & Prepayments
            {adjustmentsCount > 0 && (
              <Badge variant="secondary" className="px-1.5 py-0 h-4 text-[10px]">
                {adjustmentsCount}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="schedule" className="mt-4">
          <ScheduleView
            planId={plan.id}
            schedules={schedules}
            activeScheduleId={activeScheduleId}
            onSelectSchedule={setActiveScheduleId}
            onScheduleDeleted={handleScheduleDeleted}
            onScheduleSaved={handleScheduleSaved}
          />
        </TabsContent>

        <TabsContent value="adjustments" className="mt-4">
          <AdjustmentsView
            plan={plan}
            onPlanUpdated={handlePlanUpdated}
            onGenerateSchedule={() => generateMutation.mutate()}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
