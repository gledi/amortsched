import { useState } from "react";
import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeftIcon,
  BookmarkCheckIcon,
  CopyIcon,
  DownloadIcon,
  LayersIcon,
  LineChartIcon,
  PiggyBankIcon,
  PlayIcon,
  PrinterIcon,
  RefreshCwIcon,
  SlidersHorizontalIcon,
  Trash2Icon,
} from "lucide-react";
import { AdjustmentsView } from "@/components/AdjustmentsView";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EditPlanDialog } from "@/components/EditPlanDialog";
import { ScheduleView } from "@/components/ScheduleView";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatCurrency, formatDate, formatPercent, formatTerm } from "@/lib/formatters";
import { loanTypeLabel } from "@/lib/plan-form";
import { plansApi } from "@/lib/plans-api";
import type { Plan, Schedule } from "@/lib/types";

export const Route = createFileRoute("/_app/plans/$planId")({
  component: PlanDetailPage,
});

interface StatProps {
  label: string;
  value: React.ReactNode;
  detail?: React.ReactNode;
  emphasis?: boolean;
}

function Stat({ label, value, detail, emphasis }: StatProps) {
  return (
    <Card size="sm">
      <CardHeader className="pb-1">
        <CardDescription>{label}</CardDescription>
        <CardTitle className={emphasis ? "text-base font-bold text-primary" : "text-base font-bold"}>{value}</CardTitle>
        {detail ? <p className="text-[11px] text-muted-foreground">{detail}</p> : null}
      </CardHeader>
    </Card>
  );
}

function PlanOverview({ plan }: { plan: Plan }) {
  const money = (value: string | number | null | undefined) => formatCurrency(value, plan.currency);
  const housing = plan.monthly_housing;
  const firstChange = [...plan.interest_rate_changes].sort((a, b) =>
    a.effective_date.localeCompare(b.effective_date),
  )[0];
  const totalMonthly = Number(plan.monthly_payment) + (housing ? Number(housing.total) : 0);
  const earlyFees = plan.early_payment_fees;
  const hasEarlyFee = Number(earlyFees.fixed) > 0 || Number(earlyFees.percent) > 0;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
      <Stat
        label="Loan amount"
        value={money(plan.amount)}
        emphasis
        detail={
          plan.down_payment !== null ? `${money(plan.down_payment)} down · ${formatPercent(plan.ltv)} LTV` : undefined
        }
      />
      <Stat
        label="Interest rate"
        value={formatPercent(plan.interest_rate)}
        detail={
          firstChange
            ? `→ ${formatPercent(firstChange.rate)} from ${formatDate(firstChange.effective_date)}`
            : "Fixed for the full term"
        }
      />
      <Stat label="Term" value={formatTerm(plan.term)} detail={`First payment ${formatDate(plan.start_date)}`} />
      <Stat label="Loan payment" value={money(plan.monthly_payment)} detail="Principal & interest / month" />
      <Stat
        label="Total monthly"
        value={money(totalMonthly)}
        detail={
          housing
            ? [
                Number(housing.property_tax) > 0 ? `tax ${money(housing.property_tax)}` : null,
                Number(housing.insurance) > 0 ? `ins. ${money(housing.insurance)}` : null,
                Number(housing.hoa) > 0 ? `HOA ${money(housing.hoa)}` : null,
                Number(housing.pmi) > 0 ? `PMI ${money(housing.pmi)}` : null,
              ]
                .filter(Boolean)
                .join(" · ") || "No ownership costs"
            : "No ownership costs"
        }
      />
      <Stat
        label="Fees"
        value={money(plan.upfront_fees ?? 0)}
        detail={
          hasEarlyFee
            ? `Prepayment: ${money(earlyFees.fixed)} + ${formatPercent(earlyFees.percent)}`
            : "No prepayment penalty"
        }
      />
    </div>
  );
}

function PlanDetailPage() {
  const { planId } = Route.useParams();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<string>("schedule");
  const [activeScheduleId, setActiveScheduleId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const {
    data: plan,
    isLoading,
    error: planError,
  } = useQuery({
    queryKey: ["plan", planId],
    queryFn: () => plansApi.getPlan(planId),
  });

  const { data: schedules = [] } = useQuery({
    queryKey: ["schedules", planId],
    queryFn: () => plansApi.listSchedules(planId),
  });

  const onError = (err: Error) => setActionError(err.message);

  const generate = useMutation({
    mutationFn: () => plansApi.generateSchedule(planId),
    onSuccess: (newSchedule) => {
      queryClient.setQueryData<Schedule[]>(["schedules", planId], (prev = []) => [
        newSchedule,
        ...prev.filter((s) => s.id !== newSchedule.id),
      ]);
      setActiveScheduleId(newSchedule.id);
      setActiveTab("schedule");
    },
    onError,
  });

  const savePlan = useMutation({
    mutationFn: () => plansApi.savePlan(planId),
    onSuccess: (updatedPlan) => {
      queryClient.setQueryData(["plan", planId], updatedPlan);
      void queryClient.invalidateQueries({ queryKey: ["plans"] });
    },
    onError,
  });

  const duplicate = useMutation({
    mutationFn: () => plansApi.duplicatePlan(planId),
    onSuccess: (copy) => {
      void queryClient.invalidateQueries({ queryKey: ["plans"] });
      router.navigate({ to: "/plans/$planId", params: { planId: copy.id } });
    },
    onError,
  });

  const exportCsv = useMutation({ mutationFn: () => plansApi.exportScheduleCsv(planId), onError });

  if (isLoading) {
    return (
      <div className="mx-auto flex max-w-7xl flex-col gap-6" role="status" aria-label="Loading plan">
        <Skeleton className="h-12 w-1/2" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (planError || !plan) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center gap-3">
        <p className="text-sm font-semibold text-destructive">Couldn&apos;t load this plan</p>
        <p className="text-xs text-muted-foreground">It may have been deleted.</p>
        <Link to="/" className={buttonVariants({ variant: "outline", size: "sm" })}>
          <ArrowLeftIcon data-icon="inline-start" />
          Back to plans
        </Link>
      </div>
    );
  }

  const isDraft = plan.status === "draft";
  const adjustmentsCount =
    plan.one_time_extra_payments.length + plan.recurring_extra_payments.length + plan.interest_rate_changes.length;

  function handlePlanUpdated(updatedPlan: Plan) {
    queryClient.setQueryData(["plan", planId], updatedPlan);
    void queryClient.invalidateQueries({ queryKey: ["plans"] });
  }

  function handleScheduleDeleted(deletedId: string) {
    queryClient.setQueryData<Schedule[]>(["schedules", planId], (prev = []) => prev.filter((s) => s.id !== deletedId));
    if (activeScheduleId === deletedId) setActiveScheduleId(null);
  }

  function handleScheduleSaved(savedSchedule: Schedule) {
    queryClient.setQueryData<Schedule[]>(["schedules", planId], (prev = []) =>
      prev.map((s) => (s.id === savedSchedule.id ? savedSchedule : s)),
    );
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div className="flex flex-col gap-1">
          <Link
            to="/"
            search={{ compare: undefined }}
            className="flex w-fit items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground print:hidden"
          >
            <ArrowLeftIcon className="size-3" />
            Plans
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">{plan.lender || plan.name}</h1>
            <Badge variant="secondary">{loanTypeLabel(plan.loan_type)}</Badge>
            <Badge variant={isDraft ? "outline" : "default"}>{isDraft ? "Draft" : "Saved"}</Badge>
            <Badge variant="outline" className="font-mono">
              {plan.currency}
            </Badge>
          </div>
          {plan.lender ? <p className="text-sm text-muted-foreground">{plan.name}</p> : null}
        </div>

        <div className="flex flex-wrap items-center gap-2 print:hidden">
          <Button size="sm" onClick={() => generate.mutate()} disabled={generate.isPending}>
            <PlayIcon data-icon="inline-start" />
            {generate.isPending ? "Calculating..." : "Generate schedule"}
          </Button>
          {isDraft ? (
            <Button variant="outline" size="sm" onClick={() => savePlan.mutate()} disabled={savePlan.isPending}>
              <BookmarkCheckIcon data-icon="inline-start" />
              {savePlan.isPending ? "Saving..." : "Mark as saved"}
            </Button>
          ) : null}
          <EditPlanDialog plan={plan} onPlanUpdated={handlePlanUpdated} />
          <Button variant="outline" size="sm" onClick={() => duplicate.mutate()} disabled={duplicate.isPending}>
            <CopyIcon data-icon="inline-start" />
            Duplicate
          </Button>
          <Button variant="outline" size="sm" onClick={() => exportCsv.mutate()} disabled={exportCsv.isPending}>
            <DownloadIcon data-icon="inline-start" />
            CSV
          </Button>
          <Button variant="outline" size="sm" onClick={() => window.print()}>
            <PrinterIcon data-icon="inline-start" />
            Print
          </Button>
          <ConfirmDialog
            title={`Delete "${plan.name}"?`}
            description="The plan and all of its schedules are removed. This cannot be undone."
            confirmLabel="Delete plan"
            onConfirm={async () => {
              await plansApi.deletePlan(planId);
              queryClient.removeQueries({ queryKey: ["plan", planId] });
              await queryClient.invalidateQueries({ queryKey: ["plans"] });
              router.navigate({ to: "/" });
            }}
            trigger={
              <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                <Trash2Icon data-icon="inline-start" />
                Delete
              </Button>
            }
          />
        </div>
      </div>

      {actionError ? (
        <Alert variant="destructive">
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      ) : null}

      <PlanOverview plan={plan} />

      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground print:hidden">
        <LineChartIcon className="size-3.5" />
        <span>Analyze this loan:</span>
        <Link
          to="/tools/refinance"
          search={{ plan: plan.id }}
          className={buttonVariants({ variant: "link", size: "xs", className: "px-0" })}
        >
          <RefreshCwIcon data-icon="inline-start" />
          Should I refinance?
        </Link>
        <Link
          to="/tools/prepay-vs-invest"
          search={{ plan: plan.id }}
          className={buttonVariants({ variant: "link", size: "xs", className: "px-0" })}
        >
          <PiggyBankIcon data-icon="inline-start" />
          Prepay or invest?
        </Link>
        <Link
          to="/"
          search={{ compare: plan.id }}
          className={buttonVariants({ variant: "link", size: "xs", className: "px-0" })}
        >
          Compare with other offers
        </Link>
      </div>

      <Tabs value={activeTab} onValueChange={(val) => val && setActiveTab(val)}>
        <TabsList className="print:hidden">
          <TabsTrigger value="schedule" className="gap-2">
            <LayersIcon className="size-3.5" />
            Schedule
            {schedules.length > 0 ? (
              <Badge variant="secondary" className="h-4 px-1.5 py-0 text-[10px]">
                {schedules.length}
              </Badge>
            ) : null}
          </TabsTrigger>
          <TabsTrigger value="adjustments" className="gap-2">
            <SlidersHorizontalIcon className="size-3.5" />
            Extra payments &amp; rate changes
            {adjustmentsCount > 0 ? (
              <Badge variant="secondary" className="h-4 px-1.5 py-0 text-[10px]">
                {adjustmentsCount}
              </Badge>
            ) : null}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="schedule" className="mt-4">
          <ScheduleView
            planId={plan.id}
            currency={plan.currency}
            schedules={schedules}
            activeScheduleId={activeScheduleId}
            onSelectSchedule={setActiveScheduleId}
            onScheduleDeleted={handleScheduleDeleted}
            onScheduleSaved={handleScheduleSaved}
          />
        </TabsContent>

        <TabsContent value="adjustments" className="mt-4">
          <AdjustmentsView plan={plan} onPlanUpdated={handlePlanUpdated} onGenerateSchedule={() => generate.mutate()} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
