import { DEFAULT_CURRENCY, getDisplayLocale } from "./currency";
import type { Term } from "./types";

function toNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined || value === "") return 0;
  const num = typeof value === "number" ? value : parseFloat(value);
  return isNaN(num) ? 0 : num;
}

export function formatCurrency(
  amount: string | number | null | undefined,
  currency: string | null | undefined = DEFAULT_CURRENCY,
): string {
  const code = currency || DEFAULT_CURRENCY;
  try {
    return new Intl.NumberFormat(getDisplayLocale(), {
      style: "currency",
      currency: code,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(toNumber(amount));
  } catch {
    return `${toNumber(amount).toFixed(2)} ${code}`;
  }
}

export function formatCompactCurrency(
  amount: string | number | null | undefined,
  currency: string | null | undefined = DEFAULT_CURRENCY,
): string {
  try {
    return new Intl.NumberFormat(getDisplayLocale(), {
      style: "currency",
      currency: currency || DEFAULT_CURRENCY,
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(toNumber(amount));
  } catch {
    return formatCurrency(amount, currency);
  }
}

export function formatPercent(rate: string | number | null | undefined): string {
  if (rate === null || rate === undefined || rate === "") return "0.00%";
  const num = typeof rate === "number" ? rate : parseFloat(rate);
  if (isNaN(num)) return "0.00%";
  return `${num.toFixed(2)}%`;
}

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return "-";
  try {
    const [year, month, day] = dateString.split("-").map(Number);
    if (!year || !month) return dateString;
    const date = new Date(year, month - 1, day || 1);
    return date.toLocaleDateString(getDisplayLocale(), {
      year: "numeric",
      month: "short",
      day: day ? "numeric" : undefined,
    });
  } catch {
    return dateString;
  }
}

export function formatTerm(term: Term | null | undefined): string {
  if (!term) return "-";
  const parts: string[] = [];
  if (term.years > 0) parts.push(`${term.years} ${term.years === 1 ? "yr" : "yrs"}`);
  if (term.months > 0) parts.push(`${term.months} ${term.months === 1 ? "mo" : "mos"}`);
  return parts.length > 0 ? parts.join(" ") : "0 mos";
}

export function formatMonths(totalMonths: number): string {
  const years = Math.floor(totalMonths / 12);
  const months = totalMonths % 12;
  const parts: string[] = [];
  if (years > 0) parts.push(`${years} ${years === 1 ? "yr" : "yrs"}`);
  if (months > 0 || parts.length === 0) parts.push(`${months} ${months === 1 ? "mo" : "mos"}`);
  return parts.join(" ");
}

export function formatMonthsToYears(totalMonths: number): string {
  return `${formatMonths(totalMonths)} (${totalMonths} payments)`;
}
