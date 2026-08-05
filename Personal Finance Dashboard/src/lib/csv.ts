import type { TxType } from "./types";

export interface CsvColumnMap {
  date?: number;
  merchant?: number;
  amount?: number;
  debit?: number;
  credit?: number;
  category?: number;
  account?: number;
}

export interface ParsedCsvRow {
  date: string;
  merchant: string;
  amount: number;
  type: TxType;
  category: string;
  account: string;
}

export interface CsvParseResult {
  headers: string[];
  previewRows: string[][];
  mapping: CsvColumnMap;
  ambiguous: boolean;
  rows: ParsedCsvRow[];
  skipped: number;
  needsReview: number;
}

function splitCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        cur += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

function normalizeHeader(h: string): string {
  return h.trim().toLowerCase().replace(/[\s_]+/g, " ");
}

const DATE_HEADERS = ["date", "transaction date", "posted date", "posting date"];
const MERCHANT_HEADERS = [
  "description",
  "merchant",
  "payee",
  "name",
  "memo",
  "details",
];
const AMOUNT_HEADERS = ["amount", "transaction amount", "value"];
const DEBIT_HEADERS = ["debit", "withdrawal", "outflow"];
const CREDIT_HEADERS = ["credit", "deposit", "inflow"];
const CATEGORY_HEADERS = ["category", "type", "classification"];
const ACCOUNT_HEADERS = ["account", "account name", "card"];

function findCol(headers: string[], candidates: string[]): number | undefined {
  for (let i = 0; i < headers.length; i++) {
    if (candidates.includes(headers[i])) return i;
  }
  return undefined;
}

export function detectMapping(rawHeaders: string[]): {
  mapping: CsvColumnMap;
  ambiguous: boolean;
} {
  const headers = rawHeaders.map(normalizeHeader);
  const mapping: CsvColumnMap = {
    date: findCol(headers, DATE_HEADERS),
    merchant: findCol(headers, MERCHANT_HEADERS),
    amount: findCol(headers, AMOUNT_HEADERS),
    debit: findCol(headers, DEBIT_HEADERS),
    credit: findCol(headers, CREDIT_HEADERS),
    category: findCol(headers, CATEGORY_HEADERS),
    account: findCol(headers, ACCOUNT_HEADERS),
  };
  const hasAmount =
    mapping.amount !== undefined ||
    (mapping.debit !== undefined && mapping.credit !== undefined);
  const ambiguous =
    mapping.date === undefined ||
    mapping.merchant === undefined ||
    !hasAmount;
  return { mapping, ambiguous };
}

function parseDate(raw: string): string | null {
  const s = raw.trim();
  if (!s) return null;
  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(s);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
  const us = /^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/.exec(s);
  if (us) {
    let y = Number(us[3]);
    if (y < 100) y += 2000;
    const m = String(Number(us[1])).padStart(2, "0");
    const d = String(Number(us[2])).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }
  const eu = /^(\d{1,2})-(\d{1,2})-(\d{2,4})$/.exec(s);
  if (eu) {
    let y = Number(eu[3]);
    if (y < 100) y += 2000;
    const d = String(Number(eu[1])).padStart(2, "0");
    const m = String(Number(eu[2])).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }
  const parsed = new Date(s);
  if (!Number.isNaN(parsed.getTime())) {
    const y = parsed.getFullYear();
    const m = String(parsed.getMonth() + 1).padStart(2, "0");
    const d = String(parsed.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }
  return null;
}

function parseAmount(raw: string): number | null {
  const cleaned = raw.replace(/[$,\s]/g, "").replace(/^\((.+)\)$/, "-$1");
  if (!cleaned) return null;
  const n = Number(cleaned);
  if (!Number.isFinite(n)) return null;
  return n;
}

export function parseCsvText(
  text: string,
  overrideMap?: CsvColumnMap
): CsvParseResult {
  const lines = text
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .filter((l) => l.trim().length > 0);
  if (lines.length < 2) {
    return {
      headers: [],
      previewRows: [],
      mapping: {},
      ambiguous: true,
      rows: [],
      skipped: 0,
      needsReview: 0,
    };
  }
  const headers = splitCsvLine(lines[0]);
  const detected = detectMapping(headers);
  const mapping = overrideMap
    ? { ...detected.mapping, ...overrideMap }
    : detected.mapping;
  const ambiguous = overrideMap ? false : detected.ambiguous;
  const previewRows = lines.slice(1, 6).map(splitCsvLine);
  const rows: ParsedCsvRow[] = [];
  let skipped = 0;
  let needsReview = 0;

  if (ambiguous && !overrideMap) {
    return {
      headers,
      previewRows,
      mapping,
      ambiguous: true,
      rows: [],
      skipped: 0,
      needsReview: 0,
    };
  }

  for (const line of lines.slice(1)) {
    const cols = splitCsvLine(line);
    const dateRaw = mapping.date !== undefined ? cols[mapping.date] || "" : "";
    const merchantRaw =
      mapping.merchant !== undefined ? cols[mapping.merchant] || "" : "";
    const date = parseDate(dateRaw);
    const merchant = merchantRaw.trim();
    if (!date || !merchant) {
      skipped++;
      continue;
    }

    let amount = 0;
    let type: TxType = "expense";
    if (mapping.amount !== undefined) {
      const n = parseAmount(cols[mapping.amount] || "");
      if (n == null) {
        skipped++;
        continue;
      }
      if (n < 0) {
        type = "expense";
        amount = Math.abs(n);
      } else {
        type = "income";
        amount = Math.abs(n);
      }
    } else {
      const debit =
        mapping.debit !== undefined
          ? parseAmount(cols[mapping.debit] || "")
          : null;
      const credit =
        mapping.credit !== undefined
          ? parseAmount(cols[mapping.credit] || "")
          : null;
      if (debit && debit !== 0) {
        type = "expense";
        amount = Math.abs(debit);
      } else if (credit && credit !== 0) {
        type = "income";
        amount = Math.abs(credit);
      } else {
        skipped++;
        continue;
      }
    }

    if (!(amount > 0) || !Number.isFinite(amount)) {
      skipped++;
      continue;
    }

    let category =
      mapping.category !== undefined
        ? (cols[mapping.category] || "").trim()
        : "";
    if (!category) {
      category = "Needs review";
      needsReview++;
    }
    const account =
      mapping.account !== undefined
        ? (cols[mapping.account] || "").trim() || "Imported account"
        : "Imported account";

    rows.push({ date, merchant, amount, type, category, account });
  }

  return {
    headers,
    previewRows,
    mapping,
    ambiguous: false,
    rows,
    skipped,
    needsReview,
  };
}
