import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  AlertTriangleIcon,
  BookmarkCheckIcon,
  CheckCircle2Icon,
  ClockIcon,
  DollarSignIcon,
  HomeIcon,
  LayersIcon,
  PercentIcon,
  ShieldIcon,
  Trash2Icon,
} from "lucide-react";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getDisplayLocale } from "@/lib/currency";
import { formatCurrency, formatMonthsToYears } from "@/lib/formatters";
import { plansApi } from "@/lib/plans-api";
import type { Installment, Schedule } from "@/lib/types";

interface ScheduleViewProps {
  planId: string;
  currency: string;
  schedules: Schedule[];
  activeScheduleId: string | null;
  onSelectSchedule: (scheduleId: string) => void;
  onScheduleDeleted: (scheduleId: string) => void;
  onScheduleSaved: (updatedSchedule: Schedule) => void;
}

function matchesSearch(inst: Installment, term: string): boolean {
  const needle = term.toLowerCase();
  return (
    inst.month_name.toLowerCase().includes(needle) ||
    String(inst.year).includes(needle) ||
    inst.type.toLowerCase().includes(needle) ||
    (inst.installment_number !== null && String(inst.installment_number).includes(needle))
  );
}

function TypeBadge({ type }: { type: string }) {
  if (type === "recurring_extra") return <Badge variant="secondary">Recurring extra</Badge>;
  if (type === "one_time_extra") return <Badge variant="outline">Extra payment</Badge>;
  return <span className="text-xs text-muted-foreground">Regular</span>;
}

interface KpiProps {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  tone?: string;
}

function Kpi({ label, value, icon, tone = "" }: KpiProps) {
  return (
    <Card size="sm">
      <CardHeader className="pb-1">
        <CardDescription className="flex items-center gap-1">
          {icon}
          {label}
        </CardDescription>
        <CardTitle className={`text-base font-bold ${tone}`}>{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}

export function ScheduleView({
  planId,
  currency,
  schedules,
  activeScheduleId,
  onSelectSchedule,
  onScheduleDeleted,
  onScheduleSaved,
}: ScheduleViewProps) {
  const [filterYear, setFilterYear] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const money = (value: string | number | null | undefined) => formatCurrency(value, currency);

  const activeSchedule = useMemo(
    () => schedules.find((s) => s.id === activeScheduleId) ?? schedules[0] ?? null,
    [schedules, activeScheduleId],
  );

  const availableYears = useMemo(() => {
    if (!activeSchedule) return [];
    return Array.from(new Set(activeSchedule.installments.map((inst) => inst.year))).sort((a, b) => a - b);
  }, [activeSchedule]);

  const filteredInstallments = useMemo(() => {
    if (!activeSchedule) return [];
    return activeSchedule.installments.filter((inst) => {
      if (filterYear !== "all" && inst.year !== parseInt(filterYear, 10)) return false;
      return searchTerm.trim() ? matchesSearch(inst, searchTerm.trim()) : true;
    });
  }, [activeSchedule, filterYear, searchTerm]);

  const save = useMutation({
    mutationFn: () => plansApi.saveSchedule(planId, activeSchedule!.id),
    onSuccess: onScheduleSaved,
  });

  if (!activeSchedule) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <LayersIcon className="mb-3 size-10 text-muted-foreground/50" />
          <h3 className="text-sm font-semibold">No schedule yet</h3>
          <p className="mt-1 max-w-sm text-xs text-muted-foreground">
            Generate a schedule to see every payment, how much goes to principal and interest, and when the loan is paid
            off.
          </p>
        </CardContent>
      </Card>
    );
  }

  const totals = activeSchedule.totals;
  const showHousing = activeSchedule.installments.some((inst) => inst.housing !== null);
  const hasPmi = totals !== null && Number(totals.pmi) > 0;
  const timeFormat = new Intl.DateTimeFormat(getDisplayLocale(), { dateStyle: "medium", timeStyle: "short" });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center print:hidden">
        <div className="flex items-center gap-3">
          {schedules.length > 1 ? (
            <div className="flex items-center gap-2">
              <span className="whitespace-nowrap text-xs font-medium text-muted-foreground">Run:</span>
              <Select value={activeSchedule.id} onValueChange={(val) => val && onSelectSchedule(val)}>
                <SelectTrigger className="w-60">
                  <SelectValue>{timeFormat.format(new Date(activeSchedule.generated_at))}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {schedules.map((s, idx) => (
                      <SelectItem key={s.id} value={s.id}>
                        #{schedules.length - idx} · {timeFormat.format(new Date(s.generated_at))}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          ) : (
            <span className="text-xs text-muted-foreground">
              Generated {timeFormat.format(new Date(activeSchedule.generated_at))}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => save.mutate()} disabled={save.isPending}>
            <BookmarkCheckIcon data-icon="inline-start" />
            {save.isPending ? "Saving..." : "Keep this run"}
          </Button>
          <ConfirmDialog
            title="Delete this schedule run?"
            description="The plan stays as it is. You can generate a new schedule at any time."
            confirmLabel="Delete run"
            onConfirm={async () => {
              await plansApi.deleteSchedule(planId, activeSchedule.id);
              onScheduleDeleted(activeSchedule.id);
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

      {save.isError ? (
        <Alert variant="destructive">
          <AlertDescription>{save.error.message}</AlertDescription>
        </Alert>
      ) : null}

      {totals ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <Kpi
            label="Total paid to lender"
            icon={<DollarSignIcon className="size-3" />}
            value={money(totals.total_outflow)}
          />
          <Kpi
            label="Total interest"
            icon={<PercentIcon className="size-3" />}
            value={money(totals.interest)}
            tone="text-destructive"
          />
          {hasPmi ? (
            <Kpi label="Total PMI" icon={<ShieldIcon className="size-3" />} value={money(totals.pmi)} />
          ) : (
            <Kpi label="Fees paid" value={money(totals.fees)} />
          )}
          {showHousing ? (
            <Kpi label="Tax, insurance & HOA" icon={<HomeIcon className="size-3" />} value={money(totals.escrow)} />
          ) : (
            <Kpi label="Principal paid" value={money(totals.principal)} tone="text-primary" />
          )}
          <Kpi label="Duration" icon={<ClockIcon className="size-3" />} value={formatMonthsToYears(totals.months)} />
          <Card size="sm">
            <CardHeader className="pb-1">
              <CardDescription>Payoff</CardDescription>
              <div className="mt-1">
                {totals.paid_off ? (
                  <Badge className="gap-1 bg-emerald-600 hover:bg-emerald-600">
                    <CheckCircle2Icon className="size-3" />
                    Paid off
                  </Badge>
                ) : (
                  <Badge variant="destructive" className="gap-1">
                    <AlertTriangleIcon className="size-3" />
                    Balance remains
                  </Badge>
                )}
              </div>
            </CardHeader>
          </Card>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <CardTitle>Payments</CardTitle>
              <CardDescription>
                {filteredInstallments.length} payment{filteredInstallments.length === 1 ? "" : "s"}
                {filterYear !== "all" ? ` in ${filterYear}` : ""}
              </CardDescription>
            </div>

            <div className="flex items-center gap-3 print:hidden">
              {availableYears.length > 1 ? (
                <div className="flex items-center gap-1.5">
                  <span className="whitespace-nowrap text-xs text-muted-foreground">Year:</span>
                  <Select value={filterYear} onValueChange={(v) => v && setFilterYear(v)}>
                    <SelectTrigger className="w-28">
                      <SelectValue>{filterYear === "all" ? "All years" : filterYear}</SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem value="all">All years</SelectItem>
                        {availableYears.map((yr) => (
                          <SelectItem key={yr} value={String(yr)}>
                            {yr}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </div>
              ) : null}
              <Input
                placeholder="Filter payments..."
                aria-label="Filter payments"
                className="w-44 sm:w-56"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="max-h-[600px] overflow-auto border-t border-border print:max-h-none print:overflow-visible">
            <Table>
              <TableHeader className="sticky top-0 z-10 bg-card shadow-xs">
                <TableRow>
                  <TableHead className="w-12 text-center">#</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Loan payment</TableHead>
                  <TableHead className="text-right">Principal</TableHead>
                  <TableHead className="text-right">Interest</TableHead>
                  <TableHead className="text-right">Fees</TableHead>
                  {showHousing ? <TableHead className="text-right">Tax, ins. & HOA</TableHead> : null}
                  {hasPmi ? <TableHead className="text-right">PMI</TableHead> : null}
                  {showHousing ? <TableHead className="text-right">Total monthly</TableHead> : null}
                  <TableHead className="text-right">Balance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredInstallments.map((inst, index) => (
                  <TableRow
                    key={`${inst.year}-${inst.month}-${inst.installment_number}-${index}`}
                    className={inst.installment_number === null ? "bg-muted/30" : undefined}
                  >
                    <TableCell className="text-center font-mono text-muted-foreground">
                      {inst.installment_number ?? "—"}
                    </TableCell>
                    <TableCell className="whitespace-nowrap font-medium">
                      {inst.month_name} {inst.year}
                    </TableCell>
                    <TableCell>
                      <TypeBadge type={inst.type} />
                    </TableCell>
                    <TableCell className="text-right font-mono font-medium">{money(inst.total)}</TableCell>
                    <TableCell className="text-right font-mono text-primary">{money(inst.principal)}</TableCell>
                    <TableCell className="text-right font-mono text-destructive">{money(inst.interest)}</TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {Number(inst.fees) > 0 ? money(inst.fees) : "—"}
                    </TableCell>
                    {showHousing ? (
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {inst.housing
                          ? money(
                              Number(inst.housing.property_tax) +
                                Number(inst.housing.insurance) +
                                Number(inst.housing.hoa),
                            )
                          : "—"}
                      </TableCell>
                    ) : null}
                    {hasPmi ? (
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {inst.housing && Number(inst.housing.pmi) > 0 ? money(inst.housing.pmi) : "—"}
                      </TableCell>
                    ) : null}
                    {showHousing ? (
                      <TableCell className="text-right font-mono font-semibold">
                        {money(inst.total_with_housing)}
                      </TableCell>
                    ) : null}
                    <TableCell className="text-right font-mono font-semibold">{money(inst.balance.after)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
              {totals && filterYear === "all" && !searchTerm ? (
                <TableFooter className="sticky bottom-0 bg-muted/80 font-semibold backdrop-blur-xs">
                  <TableRow>
                    <TableCell colSpan={3}>Totals</TableCell>
                    <TableCell className="text-right font-mono">{money(totals.total_outflow)}</TableCell>
                    <TableCell className="text-right font-mono text-primary">{money(totals.principal)}</TableCell>
                    <TableCell className="text-right font-mono text-destructive">{money(totals.interest)}</TableCell>
                    <TableCell className="text-right font-mono">{money(totals.fees)}</TableCell>
                    {showHousing ? (
                      <TableCell className="text-right font-mono">{money(totals.escrow)}</TableCell>
                    ) : null}
                    {hasPmi ? <TableCell className="text-right font-mono">{money(totals.pmi)}</TableCell> : null}
                    {showHousing ? (
                      <TableCell className="text-right font-mono">
                        {money(Number(totals.total_outflow) + Number(totals.escrow) + Number(totals.pmi))}
                      </TableCell>
                    ) : null}
                    <TableCell className="text-right font-mono">{money(0)}</TableCell>
                  </TableRow>
                </TableFooter>
              ) : null}
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
