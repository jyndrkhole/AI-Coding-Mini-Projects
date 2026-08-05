import type { Cadence, Transaction } from "./types";

const SUB_HINTS = [
  "netflix",
  "spotify",
  "hulu",
  "disney",
  "youtube",
  "icloud",
  "dropbox",
  "adobe",
  "microsoft",
  "amazon prime",
  "patreon",
  "membership",
  "studio",
  "gym",
  "openai",
  "chatgpt",
  "canva",
  "notion",
  "zoom",
  "slack",
  "github",
];

const BILL_HINTS = [
  "mortgage",
  "rent",
  "loan",
  "insurance",
  "utility",
  "utilities",
  "electric",
  "water",
  "internet",
  "phone",
  "mobile",
  "daycare",
  "tuition",
  "lease",
  "car payment",
  "auto payment",
  "hoa",
  "property tax",
];

export function normalizeMerchant(name: string): string {
  let s = name.toLowerCase().trim();
  s = s.replace(/[^\w\s]/g, " ");
  s = s.replace(/#\d+\b/g, " ");
  s = s.replace(/\b\d{6,}\b/g, " ");
  s = s.replace(/\s+/g, " ").trim();
  return s;
}

function classifyInterval(days: number): Cadence | null {
  if (days >= 5 && days <= 9) return "weekly";
  if (days >= 12 && days <= 17) return "biweekly";
  if (days >= 24 && days <= 40) return "monthly";
  if (days >= 75 && days <= 110) return "quarterly";
  if (days >= 330 && days <= 400) return "annual";
  return null;
}

function dayDiff(a: string, b: string): number {
  const da = new Date(a + "T00:00:00");
  const db = new Date(b + "T00:00:00");
  return Math.round((db.getTime() - da.getTime()) / 86400000);
}

function amountVariation(amounts: number[]): number {
  if (!amounts.length) return 1;
  const avg = amounts.reduce((s, n) => s + n, 0) / amounts.length;
  if (avg === 0) return 0;
  const maxDev = Math.max(...amounts.map((n) => Math.abs(n - avg) / avg));
  return maxDev;
}

function dominantInterval(intervals: number[]): number | null {
  if (!intervals.length) return null;
  const sorted = [...intervals].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

function intervalJitter(intervals: number[], dominant: number): number {
  if (!intervals.length) return 999;
  return Math.max(...intervals.map((i) => Math.abs(i - dominant)));
}

export function monthlyEquivalent(amount: number, cadence: Cadence): number {
  switch (cadence) {
    case "weekly":
      return (amount * 52) / 12;
    case "biweekly":
      return (amount * 26) / 12;
    case "monthly":
      return amount;
    case "quarterly":
      return amount / 3;
    case "annual":
      return amount / 12;
  }
}

function addCadence(dateStr: string, cadence: Cadence): string {
  const d = new Date(dateStr + "T00:00:00");
  const day = d.getDate();
  if (cadence === "weekly") d.setDate(d.getDate() + 7);
  else if (cadence === "biweekly") d.setDate(d.getDate() + 14);
  else if (cadence === "monthly") {
    d.setMonth(d.getMonth() + 1);
    if (d.getDate() !== day) d.setDate(0);
  } else if (cadence === "quarterly") {
    d.setMonth(d.getMonth() + 3);
    if (d.getDate() !== day) d.setDate(0);
  } else if (cadence === "annual") {
    d.setFullYear(d.getFullYear() + 1);
    if (d.getDate() !== day) d.setDate(0);
  }
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

export type DetectionKind = "subscription" | "recurring";

export interface DetectionSuggestion {
  key: string;
  kind: DetectionKind;
  merchant: string;
  displayMerchant: string;
  category: string;
  cadence: Cadence;
  occurrenceCount: number;
  confidence: "high" | "likely";
  averageAmount: number;
  monthlyEquivalent: number;
  nextDate: string;
}

function hasHint(haystack: string, hints: string[]): boolean {
  return hints.some((h) => haystack.includes(h));
}

export function detectPatterns(
  transactions: Transaction[],
  dismissed: string[]
): DetectionSuggestion[] {
  const dismissedSet = new Set(dismissed);
  const expenses = transactions.filter((t) => t.type === "expense");
  const groups = new Map<string, Transaction[]>();

  for (const t of expenses) {
    const key = normalizeMerchant(t.merchant);
    if (!key) continue;
    const list = groups.get(key) || [];
    list.push(t);
    groups.set(key, list);
  }

  const out: DetectionSuggestion[] = [];

  for (const [norm, list] of groups) {
    const byDate = new Map<string, Transaction>();
    for (const t of list) {
      if (!byDate.has(t.date)) byDate.set(t.date, t);
    }
    const unique = [...byDate.values()].sort((a, b) =>
      a.date.localeCompare(b.date)
    );
    if (unique.length < 2) continue;

    const intervals: number[] = [];
    for (let i = 1; i < unique.length; i++) {
      intervals.push(dayDiff(unique[i - 1].date, unique[i].date));
    }
    const dominant = dominantInterval(intervals);
    if (dominant == null) continue;
    const cadence = classifyInterval(dominant);
    if (!cadence) continue;

    const amounts = unique.map((t) => t.amount);
    const variation = amountVariation(amounts);
    const category = unique[unique.length - 1].category || "Other";
    const tagsJoined = unique
      .flatMap((t) => t.tags)
      .join(" ")
      .toLowerCase();
    const hay = `${norm} ${category.toLowerCase()} ${tagsJoined}`;

    const subHint =
      hasHint(hay, SUB_HINTS) ||
      category.toLowerCase().includes("subscription") ||
      tagsJoined.includes("subscription");
    const billHint = hasHint(hay, BILL_HINTS);

    let kind: DetectionKind | null = null;
    if (subHint && variation <= 0.2) kind = "subscription";
    else if (billHint && variation <= 0.35) kind = "recurring";
    else if (
      !subHint &&
      !billHint &&
      unique.length >= 3 &&
      (cadence === "monthly" || cadence === "quarterly" || cadence === "annual") &&
      variation <= 0.03
    ) {
      kind = "recurring";
    }

    if (!kind) continue;
    if (kind === "subscription" && variation > 0.2) continue;
    if (kind === "recurring" && !billHint && !subHint && variation > 0.03)
      continue;
    if (kind === "recurring" && billHint && variation > 0.35) continue;

    const jitter = intervalJitter(intervals, dominant);
    const confidence: "high" | "likely" =
      unique.length >= 3 && variation <= 0.12 && jitter <= 5 ? "high" : "likely";

    const avg = amounts.reduce((s, n) => s + n, 0) / amounts.length;
    const displayMerchant = unique[unique.length - 1].merchant;
    const key = `${kind}:${norm}:${cadence}`;
    if (dismissedSet.has(key)) continue;

    out.push({
      key,
      kind,
      merchant: norm,
      displayMerchant,
      category,
      cadence,
      occurrenceCount: unique.length,
      confidence,
      averageAmount: Math.round(avg * 100) / 100,
      monthlyEquivalent:
        Math.round(monthlyEquivalent(avg, cadence) * 100) / 100,
      nextDate: addCadence(unique[unique.length - 1].date, cadence),
    });
  }

  return out.sort((a, b) => b.monthlyEquivalent - a.monthlyEquivalent);
}
