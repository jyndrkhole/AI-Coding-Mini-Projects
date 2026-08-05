import type { AppState, PeriodKey, Transaction } from "./types";
import {
  formatMoney as formatMoneyCurrency,
  configureMoney,
  detectCurrencyFromLocation,
  CURRENCY_OPTIONS,
  DEFAULT_CURRENCY,
  DEFAULT_LOCALE,
} from "./currency";

export {
  configureMoney,
  detectCurrencyFromLocation,
  CURRENCY_OPTIONS,
  DEFAULT_CURRENCY,
  DEFAULT_LOCALE,
};

export async function fetchState(): Promise<AppState> {
  const res = await fetch("/api/state", { cache: "no-store" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to load state");
  }
  return res.json();
}

export async function savePeriod(selectedPeriod: PeriodKey) {
  const res = await fetch("/api/preferences", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selectedPeriod }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to save period");
  }
  return res.json();
}

export async function savePreferences(patch: Record<string, unknown>) {
  const res = await fetch("/api/preferences", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to save preferences");
  }
  return res.json();
}

export async function createTransaction(tx: Partial<Transaction> & Record<string, unknown>) {
  const res = await fetch("/api/transactions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(tx),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to create transaction");
  }
  return res.json();
}

export async function patchTransaction(
  id: string,
  patch: { category?: string; tags?: string[] }
) {
  const res = await fetch("/api/transactions", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, ...patch }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to update transaction");
  }
  return res.json();
}

export async function deleteTransaction(id: string) {
  const res = await fetch(`/api/transactions?id=${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to delete transaction");
  }
  return res.json();
}

export function formatMoney(n: number, currency?: string, locale?: string): string {
  return formatMoneyCurrency(n, currency, locale);
}

export function todayISO(): string {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}
