import * as React from "react";
import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableFooter,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  formatCurrency,
  formatMonthsToYears,
  formatDate,
} from "@/lib/formatters";
import { plansApi } from "@/lib/plans-api";
import type { Schedule } from "@/lib/types";
import {
  DownloadIcon,
  BookmarkCheckIcon,
  Trash2Icon,
  CheckCircle2Icon,
  AlertTriangleIcon,
  DollarSignIcon,
  PercentIcon,
  ClockIcon,
  LayersIcon,
} from "lucide-react";

interface ScheduleViewProps {
  planId: string;
  schedules: Schedule[];
  activeScheduleId: string | null;
  onSelectSchedule: (scheduleId: string) => void;
  onScheduleDeleted: (scheduleId: string) => void;
  onScheduleSaved: (updatedSchedule: Schedule) => void;
}

export function ScheduleView({
  planId,
  schedules,
  activeScheduleId,
  onSelectSchedule,
  onScheduleDeleted,
  onScheduleSaved,
}: ScheduleViewProps) {
  const [filterYear, setFilterYear] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const activeSchedule = useMemo(() => {
    if (!activeScheduleId && schedules.length > 0) return schedules[0];
    return schedules.find((s) => s.id === activeScheduleId) || schedules[0] || null;
  }, [schedules, activeScheduleId]);

  // Extract unique years from installments
  const availableYears = useMemo(() => {
    if (!activeSchedule) return [];
    const years = new Set<number>();
    activeSchedule.installments.forEach((inst) => years.add(inst.year));
    return Array.from(years).sort((a, b) => a - b);
  }, [activeSchedule]);

  // Filtered installments
  const filteredInstallments = useMemo(() => {
    if (!activeSchedule) return [];
    return activeSchedule.installments.filter((inst) => {
      if (filterYear !== "all" && inst.year !== parseInt(filterYear, 10)) {
        return false;
      }
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const matchesMonth = inst.month_name.toLowerCase().includes(term);
        const matchesYear = String(inst.year).includes(term);
        const matchesType = inst.type.toLowerCase().includes(term);
        const matchesNum = inst.installment_number !== null && String(inst.installment_number).includes(term);
        return matchesMonth || matchesYear || matchesType || matchesNum;
      }
      return true;
    });
  }, [activeSchedule, filterYear, searchTerm]);

  if (!activeSchedule) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <LayersIcon className="size-10 text-muted-foreground/50 mb-3" />
          <h3 className="text-sm font-semibold">No Schedule Generated Yet</h3>
          <p className="mt-1 text-xs text-muted-foreground max-w-sm">
            Generate an amortization schedule to inspect your monthly payment schedule, principal reduction, and interest breakdown.
          </p>
        </CardContent>
      </Card>
    );
  }

  const totals = activeSchedule.totals;

  function exportToCsv() {
    if (!activeSchedule) return;
    const headers = [
      "Installment",
      "Year",
      "Month",
      "Payment Type",
      "Principal ($)",
      "Interest ($)",
      "Fees ($)",
      "Total Payment ($)",
      "Balance Before ($)",
      "Balance After ($)",
    ];

    const rows = activeSchedule.installments.map((inst) => [
      inst.installment_number ?? "",
      inst.year,
      inst.month_name,
      inst.type,
      inst.principal,
      inst.interest,
      inst.fees,
      inst.total,
      inst.balance.before,
      inst.balance.after,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `amortization_schedule_${planId.slice(0, 8)}_${new Date(activeSchedule.generated_at).toISOString().split("T")[0]}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  async function handleSaveSchedule() {
    if (!activeSchedule) return;
    setSaving(true);
    try {
      const saved = await plansApi.saveSchedule(planId, activeSchedule.id);
      onScheduleSaved(saved);
    } catch (err: any) {
      alert(err?.message || "Failed to save schedule");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteSchedule() {
    if (!activeSchedule) return;
    if (!confirm("Are you sure you want to delete this generated schedule?")) return;
    setDeleting(true);
    try {
      await plansApi.deleteSchedule(planId, activeSchedule.id);
      onScheduleDeleted(activeSchedule.id);
    } catch (err: any) {
      alert(err?.message || "Failed to delete schedule");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Schedule selector and Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {schedules.length > 1 && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground whitespace-nowrap">Schedule:</span>
              <Select value={activeSchedule.id} onValueChange={(val) => val && onSelectSchedule(val)}>
                <SelectTrigger className="w-56">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {schedules.map((s, idx) => (
                      <SelectItem key={s.id} value={s.id}>
                        Run #{schedules.length - idx} ({new Date(s.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          )}
          <span className="text-xs text-muted-foreground">
            Generated {new Date(activeSchedule.generated_at).toLocaleString()}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={exportToCsv}>
            <DownloadIcon data-icon="inline-start" />
            Export CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSaveSchedule}
            disabled={saving}
          >
            <BookmarkCheckIcon data-icon="inline-start" />
            {saving ? "Saving..." : "Lock / Save"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDeleteSchedule}
            disabled={deleting}
            className="text-destructive hover:text-destructive"
          >
            <Trash2Icon data-icon="inline-start" />
            Delete
          </Button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      {totals && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <Card size="sm">
            <CardHeader className="pb-1">
              <CardDescription className="flex items-center gap-1">
                <DollarSignIcon className="size-3" />
                Total Outflow
              </CardDescription>
              <CardTitle className="text-base font-bold text-foreground">
                {formatCurrency(totals.total_outflow)}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card size="sm">
            <CardHeader className="pb-1">
              <CardDescription className="flex items-center gap-1">
                <PercentIcon className="size-3" />
                Total Interest
              </CardDescription>
              <CardTitle className="text-base font-bold text-destructive">
                {formatCurrency(totals.interest)}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card size="sm">
            <CardHeader className="pb-1">
              <CardDescription>Principal Paid</CardDescription>
              <CardTitle className="text-base font-bold text-primary">
                {formatCurrency(totals.principal)}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card size="sm">
            <CardHeader className="pb-1">
              <CardDescription>Fees Paid</CardDescription>
              <CardTitle className="text-base font-bold">
                {formatCurrency(totals.fees)}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card size="sm">
            <CardHeader className="pb-1">
              <CardDescription className="flex items-center gap-1">
                <ClockIcon className="size-3" />
                Duration
              </CardDescription>
              <CardTitle className="text-base font-bold">
                {formatMonthsToYears(totals.months)}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card size="sm">
            <CardHeader className="pb-1">
              <CardDescription>Payoff Status</CardDescription>
              <div className="mt-1">
                {totals.paid_off ? (
                  <Badge variant="default" className="gap-1 bg-emerald-600 hover:bg-emerald-600">
                    <CheckCircle2Icon className="size-3" />
                    Fully Paid Off
                  </Badge>
                ) : (
                  <Badge variant="destructive" className="gap-1">
                    <AlertTriangleIcon className="size-3" />
                    Unpaid Balance
                  </Badge>
                )}
              </div>
            </CardHeader>
          </Card>
        </div>
      )}

      {/* Installments Table Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <CardTitle>Installment Schedule</CardTitle>
              <CardDescription>
                Showing {filteredInstallments.length} installment{filteredInstallments.length === 1 ? "" : "s"}
                {filterYear !== "all" ? ` for Year ${filterYear}` : ""}
              </CardDescription>
            </div>

            <div className="flex items-center gap-3">
              {availableYears.length > 1 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground whitespace-nowrap">Year:</span>
                  <Select value={filterYear} onValueChange={(v) => v && setFilterYear(v)}>
                    <SelectTrigger className="w-28">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem value="all">All Years</SelectItem>
                        {availableYears.map((yr) => (
                          <SelectItem key={yr} value={String(yr)}>
                            {yr}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </div>
              )}

              <Input
                placeholder="Filter installments..."
                className="w-44 sm:w-56"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="max-h-[600px] overflow-auto border-t border-border">
            <Table>
              <TableHeader className="sticky top-0 bg-card z-10 shadow-xs">
                <TableRow>
                  <TableHead className="w-12 text-center">#</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Payment</TableHead>
                  <TableHead className="text-right">Principal</TableHead>
                  <TableHead className="text-right">Interest</TableHead>
                  <TableHead className="text-right">Fees</TableHead>
                  <TableHead className="text-right">Ending Balance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredInstallments.map((inst, index) => {
                  const isExtra =
                    inst.type.toLowerCase().includes("extra") ||
                    inst.type.toLowerCase().includes("one_time");
                  const isRecurring = inst.type.toLowerCase().includes("recurring");

                  return (
                    <TableRow
                      key={`${inst.year}-${inst.month}-${inst.installment_number}-${index}`}
                      className={isExtra ? "bg-muted/30" : undefined}
                    >
                      <TableCell className="text-center font-mono text-muted-foreground">
                        {inst.installment_number ?? "—"}
                      </TableCell>
                      <TableCell className="font-medium whitespace-nowrap">
                        {inst.month_name} {inst.year}
                      </TableCell>
                      <TableCell>
                        {isRecurring ? (
                          <Badge variant="secondary">Recurring Extra</Badge>
                        ) : isExtra ? (
                          <Badge variant="outline">Extra Payment</Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">Regular</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono font-medium">
                        {formatCurrency(inst.total)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-primary">
                        {formatCurrency(inst.principal)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-destructive">
                        {formatCurrency(inst.interest)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {parseFloat(String(inst.fees)) > 0
                          ? formatCurrency(inst.fees)
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono font-semibold">
                        {formatCurrency(inst.balance.after)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
              {totals && filterYear === "all" && !searchTerm && (
                <TableFooter className="sticky bottom-0 bg-muted/80 backdrop-blur-xs font-semibold">
                  <TableRow>
                    <TableCell colSpan={3}>Totals</TableCell>
                    <TableCell className="text-right font-mono">
                      {formatCurrency(totals.total_outflow)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-primary">
                      {formatCurrency(totals.principal)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-destructive">
                      {formatCurrency(totals.interest)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatCurrency(totals.fees)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      $0.00
                    </TableCell>
                  </TableRow>
                </TableFooter>
              )}
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
