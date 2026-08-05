import type { PeriodKey } from "./types";

function pad(n: number) {
  return String(n).padStart(2, "0");
}

export function toISODate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function parseISODate(s: string): Date {
  const [y, m, day] = s.split("-").map(Number);
  return new Date(y, (m || 1) - 1, day || 1);
}

export function isValidPeriod(v: unknown): v is PeriodKey {
  return (
    v === "all-time" ||
    v === "this-month" ||
    v === "last-month" ||
    v === "last-3-months" ||
    v === "last-6-months" ||
    v === "this-year"
  );
}

/** Inclusive start date for a period, or null for all-time. */
export function periodStart(period: PeriodKey, now = new Date()): string | null {
  const y = now.getFullYear();
  const m = now.getMonth();
  if (period === "all-time") return null;
  if (period === "this-month") return toISODate(new Date(y, m, 1));
  if (period === "last-month") return toISODate(new Date(y, m - 1, 1));
  if (period === "last-3-months") return toISODate(new Date(y, m - 2, 1));
  if (period === "last-6-months") return toISODate(new Date(y, m - 5, 1));
  if (period === "this-year") return toISODate(new Date(y, 0, 1));
  return null;
}

/** Inclusive end date for a period (YYYY-MM-DD). */
export function periodEnd(period: PeriodKey, now = new Date()): string {
  const y = now.getFullYear();
  const m = now.getMonth();
  if (period === "last-month") {
    return toISODate(new Date(y, m, 0));
  }
  return toISODate(now);
}

export function inPeriod(
  date: string,
  period: PeriodKey,
  now = new Date()
): boolean {
  const start = periodStart(period, now);
  const end = periodEnd(period, now);
  if (start && date < start) return false;
  if (date > end) return false;
  return true;
}

/** Prior comparable window for trend strips. */
export function priorPeriodRange(
  period: PeriodKey,
  now = new Date()
): { start: string; end: string } | null {
  const y = now.getFullYear();
  const m = now.getMonth();
  if (period === "all-time") return null;
  if (period === "this-month") {
    const start = toISODate(new Date(y, m - 1, 1));
    const end = toISODate(new Date(y, m, 0));
    return { start, end };
  }
  if (period === "last-month") {
    const start = toISODate(new Date(y, m - 2, 1));
    const end = toISODate(new Date(y, m - 1, 0));
    return { start, end };
  }
  if (period === "last-3-months") {
    const start = toISODate(new Date(y, m - 5, 1));
    const end = toISODate(new Date(y, m - 2, 0));
    return { start, end };
  }
  if (period === "last-6-months") {
    const start = toISODate(new Date(y, m - 11, 1));
    const end = toISODate(new Date(y, m - 5, 0));
    return { start, end };
  }
  if (period === "this-year") {
    const start = toISODate(new Date(y - 1, 0, 1));
    const end = toISODate(new Date(y - 1, 11, 31));
    return { start, end };
  }
  return null;
}

export function inDateRange(date: string, start: string, end: string): boolean {
  return date >= start && date <= end;
}
