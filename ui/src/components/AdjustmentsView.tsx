import type { ReactNode } from "react";
import { useState } from "react";
import {
  DollarSignIcon,
  InfoIcon,
  PencilIcon,
  PlayIcon,
  PlusIcon,
  RepeatIcon,
  TrendingUpIcon,
  XIcon,
} from "lucide-react";
import { AdjustmentDialog } from "@/components/AdjustmentDialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  adjustmentsOf,
  removeAdjustment,
  upsertAdjustment,
  type AdjustmentKind,
  type AdjustmentValue,
} from "@/lib/adjustments";
import { formatCurrency, formatDate, formatPercent } from "@/lib/formatters";
import { plansApi } from "@/lib/plans-api";
import type { Adjustments, Plan } from "@/lib/types";

interface AdjustmentsViewProps {
  plan: Plan;
  onPlanUpdated: (updatedPlan: Plan) => void;
  onGenerateSchedule: () => void;
}

interface Column<T> {
  header: string;
  align?: "right";
  cell: (item: T) => ReactNode;
}

interface AdjustmentSectionProps<T extends AdjustmentValue> {
  kind: AdjustmentKind;
  title: string;
  description: string;
  icon: ReactNode;
  empty: string;
  items: T[];
  columns: Column<T>[];
  defaultDate: string;
  onSave: (kind: AdjustmentKind, value: AdjustmentValue, index?: number) => Promise<void>;
  onRemove: (kind: AdjustmentKind, index: number) => Promise<void>;
  busy: boolean;
}

function AdjustmentSection<T extends AdjustmentValue>({
  kind,
  title,
  description,
  icon,
  empty,
  items,
  columns,
  defaultDate,
  onSave,
  onRemove,
  busy,
}: AdjustmentSectionProps<T>) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="flex items-center gap-1.5">
                {icon}
                {title}
              </CardTitle>
              <Badge variant="secondary">{items.length}</Badge>
            </div>
            <CardDescription>{description}</CardDescription>
          </div>
          <AdjustmentDialog
            kind={kind}
            defaultDate={defaultDate}
            onSubmit={(value) => onSave(kind, value)}
            trigger={
              <Button size="sm" variant="outline" disabled={busy}>
                <PlusIcon data-icon="inline-start" />
                Add
              </Button>
            }
          />
        </div>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <div className="border border-dashed border-border py-8 text-center text-xs text-muted-foreground">
            {empty}
          </div>
        ) : (
          <div className="border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  {columns.map((column) => (
                    <TableHead key={column.header} className={column.align === "right" ? "text-right" : undefined}>
                      {column.header}
                    </TableHead>
                  ))}
                  <TableHead className="w-20 text-right">
                    <span className="sr-only">Actions</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item, index) => (
                  <TableRow key={`${kind}-${index}`}>
                    {columns.map((column) => (
                      <TableCell
                        key={column.header}
                        className={column.align === "right" ? "text-right font-mono" : "font-medium"}
                      >
                        {column.cell(item)}
                      </TableCell>
                    ))}
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <AdjustmentDialog
                          kind={kind}
                          initial={item}
                          defaultDate={defaultDate}
                          onSubmit={(value) => onSave(kind, value, index)}
                          trigger={
                            <Button
                              size="icon-sm"
                              variant="ghost"
                              aria-label={`Edit ${title.toLowerCase()}`}
                              disabled={busy}
                            >
                              <PencilIcon />
                            </Button>
                          }
                        />
                        <Button
                          size="icon-sm"
                          variant="ghost"
                          className="text-destructive hover:text-destructive"
                          aria-label={`Remove ${title.toLowerCase()}`}
                          disabled={busy}
                          onClick={() => void onRemove(kind, index)}
                        >
                          <XIcon />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function AdjustmentsView({ plan, onPlanUpdated, onGenerateSchedule }: AdjustmentsViewProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const adjustments = adjustmentsOf(plan);
  const currency = plan.currency;

  async function persist(next: Adjustments) {
    setBusy(true);
    setError(null);
    try {
      onPlanUpdated(await plansApi.replaceAdjustments(plan.id, next));
    } finally {
      setBusy(false);
    }
  }

  async function save(kind: AdjustmentKind, value: AdjustmentValue, index?: number) {
    await persist(upsertAdjustment(adjustments, kind, value, index));
  }

  async function remove(kind: AdjustmentKind, index: number) {
    try {
      await persist(removeAdjustment(adjustments, kind, index));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove the adjustment");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Alert variant="info" className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-2.5">
          <InfoIcon className="mt-0.5 size-4 shrink-0 text-primary" />
          <div>
            <AlertTitle>What-if adjustments</AlertTitle>
            <AlertDescription>
              Model prepayments and rate changes, then recalculate to see how much interest and time they save.
            </AlertDescription>
          </div>
        </div>
        <Button size="sm" onClick={onGenerateSchedule} className="shrink-0">
          <PlayIcon data-icon="inline-start" />
          Recalculate
        </Button>
      </Alert>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <AdjustmentSection
        kind="one_time"
        title="One-time extra payments"
        description="Lump sums applied to principal on a specific date."
        icon={<DollarSignIcon className="size-4 text-primary" />}
        empty="No one-time extra payments yet."
        items={adjustments.one_time_extra_payments}
        columns={[
          { header: "Date", cell: (item) => formatDate(item.date) },
          { header: "Amount", align: "right", cell: (item) => formatCurrency(item.amount, currency) },
        ]}
        defaultDate={plan.start_date}
        onSave={save}
        onRemove={remove}
        busy={busy}
      />

      <AdjustmentSection
        kind="recurring"
        title="Recurring extra payments"
        description="A fixed extra amount paid toward principal every month."
        icon={<RepeatIcon className="size-4 text-primary" />}
        empty="No recurring extra payments yet."
        items={adjustments.recurring_extra_payments}
        columns={[
          { header: "Starts", cell: (item) => formatDate(item.start_date) },
          { header: "Per month", align: "right", cell: (item) => formatCurrency(item.amount, currency) },
          { header: "Payments", align: "right", cell: (item) => item.count },
          {
            header: "Total extra",
            align: "right",
            cell: (item) => formatCurrency(Number(item.amount) * item.count, currency),
          },
        ]}
        defaultDate={plan.start_date}
        onSave={save}
        onRemove={remove}
        busy={busy}
      />

      <AdjustmentSection
        kind="rate_change"
        title="Interest rate changes"
        description="Model a variable or adjustable rate, or a renegotiation."
        icon={<TrendingUpIcon className="size-4 text-primary" />}
        empty={`No rate changes. The rate stays at ${formatPercent(plan.interest_rate)}.`}
        items={adjustments.interest_rate_changes}
        columns={[
          { header: "Effective", cell: (item) => formatDate(item.effective_date) },
          { header: "New rate", align: "right", cell: (item) => formatPercent(item.rate) },
        ]}
        defaultDate={plan.start_date}
        onSave={save}
        onRemove={remove}
        busy={busy}
      />
    </div>
  );
}
