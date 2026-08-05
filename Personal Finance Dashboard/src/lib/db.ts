import fs from "fs";
import path from "path";
import Database from "better-sqlite3";
import {
  DEFAULT_TIMEZONE,
  STARTER_ACCOUNTS,
  STARTER_CATEGORIES,
  type AppSettings,
  type DocumentMeta,
  type PeriodKey,
  type Rule,
  type TagRow,
  type Transaction,
} from "./types";
import { DEFAULT_CURRENCY, DEFAULT_LOCALE } from "./currency";
import { isValidPeriod } from "./periods";

export interface StmtResult {
  success: boolean;
  meta?: { changes: number };
}

export interface QueryResult<T = Record<string, unknown>> {
  results: T[];
  success: boolean;
}

/** Minimal D1-compatible database surface. */
export interface DbLike {
  prepare(sql: string): {
    bind(...args: unknown[]): {
      all<T = Record<string, unknown>>(): Promise<QueryResult<T>>;
      first<T = Record<string, unknown>>(): Promise<T | null>;
      run(): Promise<StmtResult>;
    };
    all<T = Record<string, unknown>>(): Promise<QueryResult<T>>;
    first<T = Record<string, unknown>>(): Promise<T | null>;
    run(): Promise<StmtResult>;
  };
  batch(
    statements: Array<ReturnType<DbLike["prepare"]> extends infer P ? any : never>
  ): Promise<StmtResult[]>;
}

export interface BucketLike {
  put(
    key: string,
    value: ArrayBuffer | Uint8Array | string,
    options?: { httpMetadata?: { contentType?: string }; customMetadata?: Record<string, string> }
  ): Promise<void>;
  get(key: string): Promise<{ arrayBuffer(): Promise<ArrayBuffer> } | null>;
  delete(key: string | string[]): Promise<void>;
  list(options?: { prefix?: string; limit?: number; cursor?: string }): Promise<{
    objects: { key: string }[];
    truncated: boolean;
    cursor?: string;
  }>;
}

const SCHEMA = `
CREATE TABLE IF NOT EXISTS transactions (
  id TEXT PRIMARY KEY,
  date TEXT NOT NULL,
  merchant TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'Needs review',
  amount REAL NOT NULL,
  type TEXT NOT NULL,
  account TEXT NOT NULL DEFAULT 'Imported account',
  tags TEXT NOT NULL DEFAULT '[]',
  receipt INTEGER NOT NULL DEFAULT 0,
  source TEXT NOT NULL,
  fingerprint TEXT NOT NULL UNIQUE,
  createdAt TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tags (
  name TEXT PRIMARY KEY,
  createdAt TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rules (
  id TEXT PRIMARY KEY,
  whenText TEXT NOT NULL,
  thenText TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  createdAt TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updatedAt TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  filename TEXT NOT NULL,
  mimeType TEXT NOT NULL,
  size INTEGER NOT NULL,
  objectKey TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  source TEXT NOT NULL,
  createdAt TEXT NOT NULL
);
`;

function dataDir() {
  return path.join(process.cwd(), ".data");
}

function wrapSqlite(db: Database.Database): DbLike {
  const wrapStmt = (stmt: Database.Statement) => {
    const api = {
      bind(...args: unknown[]) {
        const bound = stmt;
        return {
          async all<T = Record<string, unknown>>() {
            return { results: bound.all(...args) as T[], success: true };
          },
          async first<T = Record<string, unknown>>() {
            return (bound.get(...args) as T) ?? null;
          },
          async run() {
            const info = bound.run(...args);
            return { success: true, meta: { changes: info.changes } };
          },
        };
      },
      async all<T = Record<string, unknown>>() {
        return { results: stmt.all() as T[], success: true };
      },
      async first<T = Record<string, unknown>>() {
        return (stmt.get() as T) ?? null;
      },
      async run() {
        const info = stmt.run();
        return { success: true, meta: { changes: info.changes } };
      },
    };
    return api;
  };

  return {
    prepare(sql: string) {
      return wrapStmt(db.prepare(sql)) as ReturnType<DbLike["prepare"]>;
    },
    async batch(statements: any[]) {
      const results: StmtResult[] = [];
      const tx = db.transaction(() => {
        for (const s of statements) {
          // statements already prepared+bound with run pending — execute via internal
        }
      });
      // Our batch usage will call .run() on each; for sqlite we execute sequentially
      for (const s of statements) {
        if (s && typeof s.run === "function") {
          results.push(await s.run());
        } else if (s && s._run) {
          results.push(await s._run());
        }
      }
      void tx;
      return results;
    },
  };
}

function localBucket(): BucketLike {
  const root = path.join(dataDir(), "r2");
  fs.mkdirSync(root, { recursive: true });
  return {
    async put(key, value, options) {
      const full = path.join(root, key);
      fs.mkdirSync(path.dirname(full), { recursive: true });
      const buf =
        typeof value === "string"
          ? Buffer.from(value)
          : Buffer.from(value as ArrayBuffer);
      fs.writeFileSync(full, buf);
      if (options?.customMetadata) {
        fs.writeFileSync(full + ".meta.json", JSON.stringify(options));
      }
    },
    async get(key) {
      const full = path.join(root, key);
      if (!fs.existsSync(full)) return null;
      const buf = fs.readFileSync(full);
      return {
        async arrayBuffer() {
          return buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
        },
      };
    },
    async delete(key) {
      const keys = Array.isArray(key) ? key : [key];
      for (const k of keys) {
        const full = path.join(root, k);
        if (fs.existsSync(full)) fs.unlinkSync(full);
        if (fs.existsSync(full + ".meta.json")) fs.unlinkSync(full + ".meta.json");
      }
    },
    async list(options) {
      const prefix = options?.prefix || "";
      const objects: { key: string }[] = [];
      const walk = (dir: string, base: string) => {
        if (!fs.existsSync(dir)) return;
        for (const name of fs.readdirSync(dir)) {
          const full = path.join(dir, name);
          const rel = path.join(base, name).replace(/\\/g, "/");
          if (fs.statSync(full).isDirectory()) walk(full, rel);
          else if (!name.endsWith(".meta.json") && rel.startsWith(prefix)) {
            objects.push({ key: rel });
          }
        }
      };
      walk(root, "");
      return { objects, truncated: false };
    },
  };
}

let localDb: DbLike | null = null;

export async function getStore(): Promise<{ db: DbLike; bucket: BucketLike }> {
  // Cloudflare / Sites runtime (ignored by Next bundler)
  try {
    const spec = "cloudflare:workers";
    const mod = await import(/* webpackIgnore: true */ /* @vite-ignore */ spec);
    const env = (mod as { env?: { DB?: DbLike; BUCKET?: BucketLike } }).env;
    if (env?.DB && env?.BUCKET) {
      return { db: env.DB, bucket: env.BUCKET };
    }
    if (env?.DB) {
      return { db: env.DB, bucket: localBucket() };
    }
  } catch {
    // local Next.js / better-sqlite3
  }

  if (!localDb) {
    fs.mkdirSync(dataDir(), { recursive: true });
    const sqlite = new Database(path.join(dataDir(), "ledgerly.sqlite"));
    sqlite.pragma("journal_mode = WAL");
    localDb = wrapSqlite(sqlite);
  }
  return { db: localDb, bucket: localBucket() };
}

export async function ensureSchema(db: DbLike): Promise<void> {
  for (const stmt of SCHEMA.split(";").map((s) => s.trim()).filter(Boolean)) {
    await db.prepare(stmt).run();
  }
  await ensureDefaultSettings(db);
}

function nowIso() {
  return new Date().toISOString();
}

export function emptySettings(): AppSettings {
  return {
    categories: [...STARTER_CATEGORIES],
    accounts: [...STARTER_ACCOUNTS],
    goals: [],
    budgets: [],
    subscriptions: [],
    recurring: [],
    dismissedPatterns: [],
    assetsTotal: 0,
    liabilitiesTotal: 0,
    netWorthConfigured: false,
    selectedPeriod: "all-time",
    currency: DEFAULT_CURRENCY,
    locale: DEFAULT_LOCALE,
    driveFolder: {
      id: "",
      name: "Ledgerly Financial Inbox",
      url: "",
    },
    driveSync: {
      lastSyncedAt: null,
      status: "idle",
      imported: 0,
      duplicates: 0,
      stored: 0,
      review: 0,
      errors: [],
      schedule: {
        time: "08:00",
        timezone: DEFAULT_TIMEZONE,
        cadence: "daily",
      },
    },
    processedFileIds: [],
    driveResetAt: null,
    freshStart: false,
  };
}

async function setSetting(db: DbLike, key: string, value: unknown) {
  const updatedAt = nowIso();
  // Always JSON-encode so scalars (strings, numbers, booleans, null) round-trip safely.
  const text = JSON.stringify(value);
  await db
    .prepare(
      `INSERT INTO settings (key, value, updatedAt) VALUES (?, ?, ?)
       ON CONFLICT(key) DO UPDATE SET value = excluded.value, updatedAt = excluded.updatedAt`
    )
    .bind(key, text, updatedAt)
    .run();
}

async function getSettingRaw(db: DbLike, key: string): Promise<string | null> {
  const row = await db
    .prepare(`SELECT value FROM settings WHERE key = ?`)
    .bind(key)
    .first<{ value: string }>();
  return row?.value ?? null;
}

export async function ensureDefaultSettings(db: DbLike) {
  const defaults = emptySettings();
  const pairs: [string, unknown][] = [
    ["categories", defaults.categories],
    ["accounts", defaults.accounts],
    ["goals", defaults.goals],
    ["budgets", defaults.budgets],
    ["subscriptions", defaults.subscriptions],
    ["recurring", defaults.recurring],
    ["dismissedPatterns", defaults.dismissedPatterns],
    ["assetsTotal", defaults.assetsTotal],
    ["liabilitiesTotal", defaults.liabilitiesTotal],
    ["netWorthConfigured", defaults.netWorthConfigured],
    ["selectedPeriod", defaults.selectedPeriod],
    ["currency", defaults.currency],
    ["locale", defaults.locale],
    ["driveFolder", defaults.driveFolder],
    ["driveSync", defaults.driveSync],
    ["processedFileIds", defaults.processedFileIds],
    ["driveResetAt", defaults.driveResetAt],
    ["freshStart", defaults.freshStart],
  ];
  for (const [key, value] of pairs) {
    const existing = await getSettingRaw(db, key);
    if (existing === null) {
      await setSetting(db, key, value);
    }
  }
}

function parseJson<T>(raw: string | null, fallback: T): T {
  if (raw == null) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export async function loadSettings(db: DbLike): Promise<AppSettings> {
  const base = emptySettings();
  const rows = await db.prepare(`SELECT key, value FROM settings`).all<{
    key: string;
    value: string;
  }>();
  const map = new Map(rows.results.map((r) => [r.key, r.value]));

  base.categories = parseJson(map.get("categories") ?? null, base.categories);
  base.accounts = parseJson(map.get("accounts") ?? null, base.accounts);
  base.goals = parseJson(map.get("goals") ?? null, base.goals);
  base.budgets = parseJson(map.get("budgets") ?? null, base.budgets);
  base.subscriptions = parseJson(
    map.get("subscriptions") ?? null,
    base.subscriptions
  );
  base.recurring = parseJson(map.get("recurring") ?? null, base.recurring);
  base.dismissedPatterns = parseJson(
    map.get("dismissedPatterns") ?? null,
    base.dismissedPatterns
  );
  base.assetsTotal = Number(parseJson(map.get("assetsTotal") ?? null, 0));
  base.liabilitiesTotal = Number(
    parseJson(map.get("liabilitiesTotal") ?? null, 0)
  );
  base.netWorthConfigured = Boolean(
    parseJson(map.get("netWorthConfigured") ?? null, false)
  );
  const period = parseJson(
    map.get("selectedPeriod") ?? null,
    "all-time" as PeriodKey
  );
  base.selectedPeriod = isValidPeriod(period) ? period : "all-time";
  base.currency = parseJson(map.get("currency") ?? null, DEFAULT_CURRENCY);
  base.locale = parseJson(map.get("locale") ?? null, DEFAULT_LOCALE);
  base.driveFolder = parseJson(map.get("driveFolder") ?? null, base.driveFolder);
  base.driveSync = {
    ...base.driveSync,
    ...parseJson(map.get("driveSync") ?? null, {}),
  };
  base.processedFileIds = parseJson(
    map.get("processedFileIds") ?? null,
    base.processedFileIds
  );
  base.driveResetAt = parseJson(
    map.get("driveResetAt") ?? null,
    null as string | null
  );
  base.freshStart = Boolean(parseJson(map.get("freshStart") ?? null, false));
  return base;
}

export async function saveSetting(db: DbLike, key: string, value: unknown) {
  await setSetting(db, key, value);
}

export async function patchSettings(
  db: DbLike,
  patch: Partial<AppSettings>
): Promise<AppSettings> {
  const current = await loadSettings(db);
  const next: AppSettings = { ...current, ...patch };
  if (patch.driveSync) {
    next.driveSync = { ...current.driveSync, ...patch.driveSync };
  }
  if (patch.driveFolder !== undefined) {
    next.driveFolder = patch.driveFolder;
  }

  const keys: (keyof AppSettings)[] = [
    "categories",
    "accounts",
    "goals",
    "budgets",
    "subscriptions",
    "recurring",
    "dismissedPatterns",
    "assetsTotal",
    "liabilitiesTotal",
    "netWorthConfigured",
    "selectedPeriod",
    "currency",
    "locale",
    "driveFolder",
    "driveSync",
    "processedFileIds",
    "driveResetAt",
    "freshStart",
  ];
  for (const key of keys) {
    if (key in patch) {
      await setSetting(db, key, next[key]);
    }
  }
  return loadSettings(db);
}

function mapTx(row: Record<string, unknown>): Transaction {
  return {
    id: String(row.id),
    date: String(row.date),
    merchant: String(row.merchant),
    category: String(row.category),
    amount: Number(row.amount),
    type: row.type === "income" ? "income" : "expense",
    account: String(row.account),
    tags: parseJson(String(row.tags || "[]"), [] as string[]),
    receipt: Number(row.receipt) === 1,
    source: String(row.source),
    fingerprint: String(row.fingerprint),
    createdAt: String(row.createdAt),
  };
}

export async function listTransactions(db: DbLike, limit = 5000): Promise<Transaction[]> {
  const res = await db
    .prepare(
      `SELECT * FROM transactions ORDER BY date DESC, createdAt DESC LIMIT ?`
    )
    .bind(limit)
    .all();
  return res.results.map((r) => mapTx(r));
}

export async function getFingerprintExists(
  db: DbLike,
  fingerprint: string
): Promise<boolean> {
  const row = await db
    .prepare(`SELECT id FROM transactions WHERE fingerprint = ?`)
    .bind(fingerprint)
    .first();
  return !!row;
}

export function applyRulesToCategory(
  merchant: string,
  category: string,
  tags: string[],
  rules: Rule[]
): { category: string; tags: string[] } {
  let cat = category;
  let nextTags = [...tags];
  for (const rule of rules.filter((r) => r.enabled)) {
    const when = rule.whenText.trim().toLowerCase();
    if (!when) continue;
    if (!merchant.toLowerCase().includes(when)) continue;
    const then = rule.thenText.trim();
    // Support "category: X" / "tag: Y" or plain category name
    const catMatch = /category\s*[:=]\s*(.+)/i.exec(then);
    const tagMatch = /tag\s*[:=]\s*(.+)/i.exec(then);
    if (catMatch) cat = catMatch[1].trim();
    else if (tagMatch) {
      const t = tagMatch[1].trim();
      if (t && !nextTags.some((x) => x.toLowerCase() === t.toLowerCase())) {
        nextTags.push(t);
      }
    } else if (then) {
      cat = then;
    }
  }
  return { category: cat, tags: nextTags };
}

export async function listRules(db: DbLike): Promise<Rule[]> {
  const res = await db
    .prepare(`SELECT * FROM rules ORDER BY createdAt DESC`)
    .all();
  return res.results.map((r) => ({
    id: String(r.id),
    whenText: String(r.whenText),
    thenText: String(r.thenText),
    enabled: Number(r.enabled) === 1,
    createdAt: String(r.createdAt),
  }));
}

export async function listTags(db: DbLike): Promise<TagRow[]> {
  const res = await db
    .prepare(`SELECT * FROM tags ORDER BY name COLLATE NOCASE`)
    .all();
  return res.results.map((r) => ({
    name: String(r.name),
    createdAt: String(r.createdAt),
  }));
}

export async function upsertTag(db: DbLike, name: string) {
  const trimmed = name.trim();
  if (!trimmed) return;
  const existing = await db
    .prepare(`SELECT name FROM tags WHERE lower(name) = lower(?)`)
    .bind(trimmed)
    .first();
  if (existing) return;
  await db
    .prepare(`INSERT INTO tags (name, createdAt) VALUES (?, ?)`)
    .bind(trimmed, nowIso())
    .run();
}

export async function listDocuments(db: DbLike, limit = 100): Promise<DocumentMeta[]> {
  const res = await db
    .prepare(
      `SELECT id, filename, mimeType, size, objectKey, status, source, createdAt
       FROM documents ORDER BY createdAt DESC LIMIT ?`
    )
    .bind(limit)
    .all();
  return res.results.map((r) => ({
    id: String(r.id),
    filename: String(r.filename),
    mimeType: String(r.mimeType),
    size: Number(r.size),
    objectKey: String(r.objectKey),
    status: String(r.status),
    source: String(r.source),
    createdAt: String(r.createdAt),
  }));
}

export async function wipeAll(
  db: DbLike,
  bucket: BucketLike
): Promise<void> {
  await db.prepare(`DELETE FROM transactions`).run();
  await db.prepare(`DELETE FROM documents`).run();
  await db.prepare(`DELETE FROM rules`).run();
  await db.prepare(`DELETE FROM tags`).run();
  await db.prepare(`DELETE FROM settings`).run();

  // Delete all R2 objects
  let cursor: string | undefined;
  do {
    const listed = await bucket.list({ limit: 500, cursor });
    if (listed.objects.length) {
      await bucket.delete(listed.objects.map((o) => o.key));
    }
    cursor = listed.truncated ? listed.cursor : undefined;
  } while (cursor);

  const fresh = emptySettings();
  fresh.freshStart = true;
  fresh.driveResetAt = nowIso();
  fresh.netWorthConfigured = false;
  fresh.assetsTotal = 0;
  fresh.liabilitiesTotal = 0;
  fresh.selectedPeriod = "all-time";
  await ensureDefaultSettings(db);
  await patchSettings(db, {
    freshStart: true,
    driveResetAt: fresh.driveResetAt,
    netWorthConfigured: false,
    assetsTotal: 0,
    liabilitiesTotal: 0,
    selectedPeriod: "all-time",
    currency: DEFAULT_CURRENCY,
    locale: DEFAULT_LOCALE,
    goals: [],
    budgets: [],
    subscriptions: [],
    recurring: [],
    dismissedPatterns: [],
    processedFileIds: [],
    categories: [...STARTER_CATEGORIES],
    accounts: [...STARTER_ACCOUNTS],
  });
}
