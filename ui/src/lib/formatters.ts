import type { Term } from "./types";

export function formatCurrency(amount: string | number | null | undefined): string {
  if (amount === null || amount === undefined || amount === "") return "$0.00";
  const num = typeof amount === "number" ? amount : parseFloat(amount);
  if (isNaN(num)) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
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
    return date.toLocaleDateString("en-US", {
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

export function formatMonthsToYears(totalMonths: number): string {
  const years = Math.floor(totalMonths / 12);
  const months = totalMonths % 12;
  const parts: string[] = [];
  if (years > 0) parts.push(`${years} ${years === 1 ? "yr" : "yrs"}`);
  if (months > 0 || parts.length === 0) parts.push(`${months} ${months === 1 ? "mo" : "mos"}`);
  return `${parts.join(" ")} (${totalMonths} payments)`;
}
