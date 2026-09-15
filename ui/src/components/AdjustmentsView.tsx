import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCurrency, formatPercent, formatDate } from "@/lib/formatters";
import { AddExtraPaymentDialog } from "@/components/AddExtraPaymentDialog";
import { AddRecurringExtraPaymentDialog } from "@/components/AddRecurringExtraPaymentDialog";
import { AddInterestRateChangeDialog } from "@/components/AddInterestRateChangeDialog";
import type { Plan } from "@/lib/types";
import {
  InfoIcon,
  CalendarIcon,
  RepeatIcon,
  TrendingUpIcon,
  DollarSignIcon,
  PlayIcon,
} from "lucide-react";

interface AdjustmentsViewProps {
  plan: Plan;
  onPlanUpdated: (updatedPlan: Plan) => void;
  onGenerateSchedule: () => void;
}

export function AdjustmentsView({
  plan,
  onPlanUpdated,
  onGenerateSchedule,
}: AdjustmentsViewProps) {
  const oneTimePayments = plan.one_time_extra_payments || [];
  const recurringPayments = plan.recurring_extra_payments || [];
  const rateChanges = plan.interest_rate_changes || [];

  const totalAdjustments =
    oneTimePayments.length + recurringPayments.length + rateChanges.length;

  return (
    <div className="flex flex-col gap-6">
      <Alert variant="info" className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-2.5">
          <InfoIcon className="size-4 mt-0.5 text-primary shrink-0" />
          <div>
            <AlertTitle>Schedule Adjustments</AlertTitle>
            <AlertDescription>
              Adding extra principal payments or interest rate changes updates your plan structure.
              Click <strong className="text-foreground">Generate Schedule</strong> anytime to recalculate the amortization table.
            </AlertDescription>
          </div>
        </div>
        <Button size="sm" onClick={onGenerateSchedule} className="shrink-0">
          <PlayIcon data-icon="inline-start" />
          Recalculate Schedule
        </Button>
      </Alert>

      {/* 1. One-Time Extra Payments */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <CardTitle className="flex items-center gap-1.5">
                  <DollarSignIcon className="size-4 text-primary" />
                  One-Time Extra Payments
                </CardTitle>
                <Badge variant="secondary">{oneTimePayments.length}</Badge>
              </div>
              <CardDescription>
                Lump-sum principal reductions applied on specific installment dates.
              </CardDescription>
            </div>
            <AddExtraPaymentDialog
              planId={plan.id}
              defaultDate={plan.start_date}
              onPaymentAdded={onPlanUpdated}
            />
          </div>
        </CardHeader>
        <CardContent>
          {oneTimePayments.length === 0 ? (
            <div className="rounded-none border border-dashed border-border py-8 text-center text-xs text-muted-foreground">
              No one-time extra payments added yet.
            </div>
          ) : (
            <div className="border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Payment Date</TableHead>
                    <TableHead className="text-right">Extra Principal Amount</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {oneTimePayments.map((p, idx) => (
                    <TableRow key={`extra-${idx}-${p.date}`}>
                      <TableCell className="font-medium">
                        {formatDate(p.date)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-primary font-semibold">
                        {formatCurrency(p.amount)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 2. Recurring Extra Payments */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <CardTitle className="flex items-center gap-1.5">
                  <RepeatIcon className="size-4 text-primary" />
                  Recurring Extra Payments
                </CardTitle>
                <Badge variant="secondary">{recurringPayments.length}</Badge>
              </div>
              <CardDescription>
                Fixed monthly principal additions applied across a series of payments.
              </CardDescription>
            </div>
            <AddRecurringExtraPaymentDialog
              planId={plan.id}
              defaultDate={plan.start_date}
              onPaymentAdded={onPlanUpdated}
            />
          </div>
        </CardHeader>
        <CardContent>
          {recurringPayments.length === 0 ? (
            <div className="rounded-none border border-dashed border-border py-8 text-center text-xs text-muted-foreground">
              No recurring extra payments configured.
            </div>
          ) : (
            <div className="border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Start Date</TableHead>
                    <TableHead className="text-right">Monthly Extra Amount</TableHead>
                    <TableHead className="text-right">Payment Count</TableHead>
                    <TableHead className="text-right">Total Extra Contribution</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recurringPayments.map((r, idx) => {
                    const totalExtra =
                      (typeof r.amount === "number" ? r.amount : parseFloat(r.amount)) *
                      r.count;
                    return (
                      <TableRow key={`rec-${idx}-${r.start_date}`}>
                        <TableCell className="font-medium">
                          {formatDate(r.start_date)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-primary font-semibold">
                          {formatCurrency(r.amount)} / mo
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {r.count} months
                        </TableCell>
                        <TableCell className="text-right font-mono font-bold">
                          {formatCurrency(totalExtra)}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 3. Mid-Loan Interest Rate Changes */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <CardTitle className="flex items-center gap-1.5">
                  <TrendingUpIcon className="size-4 text-primary" />
                  Interest Rate Changes
                </CardTitle>
                <Badge variant="secondary">{rateChanges.length}</Badge>
              </div>
              <CardDescription>
                Simulate variable or renegotiated interest rates effective from given dates.
              </CardDescription>
            </div>
            <AddInterestRateChangeDialog
              planId={plan.id}
              defaultDate={plan.start_date}
              onRateChangeAdded={onPlanUpdated}
            />
          </div>
        </CardHeader>
        <CardContent>
          {rateChanges.length === 0 ? (
            <div className="rounded-none border border-dashed border-border py-8 text-center text-xs text-muted-foreground">
              No mid-loan interest rate changes added. Initial rate is {formatPercent(plan.interest_rate)}.
            </div>
          ) : (
            <div className="border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Effective Date</TableHead>
                    <TableHead className="text-right">Adjusted Annual Rate</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rateChanges.map((rc, idx) => (
                    <TableRow key={`rc-${idx}-${rc.effective_date}`}>
                      <TableCell className="font-medium">
                        {formatDate(rc.effective_date)}
                      </TableCell>
                      <TableCell className="text-right font-mono font-bold text-destructive">
                        {formatPercent(rc.rate)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
