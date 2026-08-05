export type TxType = "expense" | "income";
export type PeriodKey =
  | "all-time"
  | "this-month"
  | "last-month"
  | "last-3-months"
  | "last-6-months"
  | "this-year";

export type Cadence = "weekly" | "biweekly" | "monthly" | "quarterly" | "annual";

export interface Transaction {
  id: string;
  date: string;
  merchant: string;
  category: string;
  amount: number;
  type: TxType;
  account: string;
  tags: string[];
  receipt: boolean;
  source: string;
  fingerprint: string;
  createdAt: string;
}

export interface Rule {
  id: string;
  whenText: string;
  thenText: string;
  enabled: boolean;
  createdAt: string;
}

export interface TagRow {
  name: string;
  createdAt: string;
}

export interface DocumentMeta {
  id: string;
  filename: string;
  mimeType: string;
  size: number;
  objectKey: string;
  status: string;
  source: string;
  createdAt: string;
}

export interface Goal {
  id: string;
  name: string;
  target: number;
  current: number;
  dueDate?: string;
  note?: string;
}

export interface Budget {
  id: string;
  category: string;
  limit: number;
  active: boolean;
}

export interface RecurringItem {
  id: string;
  name: string;
  category: string;
  amount: number;
  cadence: Cadence;
  nextDate: string;
  account?: string;
  active: boolean;
}

export interface SubscriptionItem {
  id: string;
  name: string;
  category: string;
  amount: number;
  cadence: Cadence;
  nextDate: string;
  account?: string;
  active: boolean;
}

export interface AppSettings {
  categories: string[];
  accounts: string[];
  goals: Goal[];
  budgets: Budget[];
  subscriptions: SubscriptionItem[];
  recurring: RecurringItem[];
  dismissedPatterns: string[];
  assetsTotal: number;
  liabilitiesTotal: number;
  netWorthConfigured: boolean;
  selectedPeriod: PeriodKey;
  currency: string;
  locale: string;
  driveFolder: {
    id: string;
    name: string;
    url: string;
  } | null;
  driveSync: {
    lastSyncedAt: string | null;
    status: string;
    imported: number;
    duplicates: number;
    stored: number;
    review: number;
    errors: string[];
    schedule: { time: string; timezone: string; cadence: string };
  };
  processedFileIds: string[];
  driveResetAt: string | null;
  freshStart: boolean;
}

export interface AppState {
  transactions: Transaction[];
  tags: TagRow[];
  rules: Rule[];
  settings: AppSettings;
  documents: DocumentMeta[];
}

export const STARTER_CATEGORIES = [
  "Housing",
  "Groceries",
  "Shopping",
  "Dining",
  "Transportation",
  "Utilities",
  "Subscriptions",
  "Insurance",
  "Health",
  "Entertainment",
  "Income",
  "Needs review",
  "Other",
] as const;

export const STARTER_ACCOUNTS = [
  "Main Checking",
  "Everyday Visa",
  "Rewards Card",
  "Cash",
] as const;

export const PERIOD_OPTIONS: { key: PeriodKey; label: string }[] = [
  { key: "all-time", label: "All time" },
  { key: "this-month", label: "This month" },
  { key: "last-month", label: "Last month" },
  { key: "last-3-months", label: "Last 3 months" },
  { key: "last-6-months", label: "Last 6 months" },
  { key: "this-year", label: "This year" },
];

export const DEFAULT_TIMEZONE = "Asia/Kolkata";
export const DEFAULT_CURRENCY = "INR";
export const DEFAULT_LOCALE = "en-IN";
export const MAX_FILE_BYTES = 20 * 1024 * 1024;
export const WIPE_CONFIRMATION = "DELETE ALL LEDGERLY DATA";
