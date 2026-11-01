/** Small formatting helpers shared across pages. */

import { formatLongDate, MONTH_NAMES, parseIsoDate } from "@/lib/date";

/** "2024-05-06" -> "6 May 2024", without timezone drift. */
export function formatDate(isoDate: string): string {
  if (!isoDate) return "—";
  if (Number.isNaN(parseIsoDate(isoDate).getTime())) return isoDate;
  return formatLongDate(isoDate);
}

export function initials(fullName: string): string {
  return fullName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/** 2 -> "2", 0.5 -> "0.5", 4.0 -> "4". */
export function formatDays(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

/** An ISO datetime as "19 Oct 2026, 14:05". */
export function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const moneyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Salary amounts are INR on the payslip and in the payroll screens. */
export function formatMoney(value: number | string | null | undefined): string {
  const amount =
    typeof value === "string" ? Number(value) : (value ?? 0);
  return moneyFormatter.format(Number.isFinite(amount) ? amount : 0);
}

/** 10, 2026 -> "October 2026". */
export function formatPayPeriod(month: number, year: number): string {
  return `${MONTH_NAMES[month - 1] ?? month} ${year}`;
}
