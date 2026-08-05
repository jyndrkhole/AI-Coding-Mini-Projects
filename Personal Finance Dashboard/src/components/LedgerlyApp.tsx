"use client";

import { useCallback, useEffect, useState } from "react";
import {
  LayoutDashboard,
  ArrowLeftRight,
  Repeat,
  CreditCard,
  PiggyBank,
  Target,
  FileText,
  Workflow,
  Settings,
  HardDrive,
  Upload,
  Plus,
} from "lucide-react";
import type { AppState, PeriodKey, TxType } from "@/lib/types";
import {
  createTransaction,
  fetchState,
  savePeriod,
  todayISO,
  configureMoney,
} from "@/lib/client";
import { DashboardPage } from "./DashboardPage";
import { TransactionsPage } from "./TransactionsPage";
import { RecurringPage } from "./RecurringPage";
import { SubscriptionsPage } from "./SubscriptionsPage";
import { BudgetsPage } from "./BudgetsPage";
import { GoalsPage } from "./GoalsPage";
import { DocumentsPage, DriveSyncModal } from "./DocumentsPage";
import { RulesPage } from "./RulesPage";
import { SettingsPage } from "./SettingsPage";
import { Modal } from "./Modal";

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "transactions", label: "Transactions", icon: ArrowLeftRight },
  { id: "recurring", label: "Recurring", icon: Repeat },
  { id: "subscriptions", label: "Subscriptions", icon: CreditCard },
  { id: "budgets", label: "Budgets", icon: PiggyBank },
  { id: "goals", label: "Goals", icon: Target },
  { id: "documents", label: "Documents", icon: FileText },
  { id: "rules", label: "Rules", icon: Workflow },
  { id: "settings", label: "Settings", icon: Settings },
] as const;

type TabId = (typeof NAV)[number]["id"];

export function LedgerlyApp() {
  const [state, setState] = useState<AppState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabId>("dashboard");
  const [toast, setToast] = useState<{ msg: string; error?: boolean } | null>(null);
  const [savingPeriod, setSavingPeriod] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [driveOpen, setDriveOpen] = useState(false);

  const showToast = useCallback((msg: string, isError?: boolean) => {
    setToast({ msg, error: isError });
    window.setTimeout(() => setToast(null), 4200);
  }, []);

  const refresh = useCallback(async () => {
    const next = await fetchState();
    configureMoney(next.settings.currency, next.settings.locale);
    setState(next);
    setError(null);
    return next;
  }, []);

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : "Load failed"));
  }, [refresh]);

  useEffect(() => {
    if (state?.settings.currency) {
      configureMoney(state.settings.currency, state.settings.locale);
    }
  }, [state?.settings.currency, state?.settings.locale]);

  async function onPeriodChange(period: PeriodKey) {
    if (!state) return;
    const previous = state.settings.selectedPeriod;
    setState({
      ...state,
      settings: { ...state.settings, selectedPeriod: period },
    });
    setSavingPeriod(true);
    try {
      await savePeriod(period);
      await refresh();
    } catch (e) {
      setState({
        ...state,
        settings: { ...state.settings, selectedPeriod: previous },
      });
      showToast(e instanceof Error ? e.message : "Could not save period", true);
    } finally {
      setSavingPeriod(false);
    }
  }

  if (error && !state) {
    return (
      <div className="loading-screen">
        <div className="card" style={{ maxWidth: 420 }}>
          <h1 style={{ marginTop: 0 }}>Personal Finance Dashboard</h1>
          <p>Could not load your data. {error}</p>
          <button type="button" className="btn btn-primary" onClick={() => refresh()}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!state) {
    return <div className="loading-screen">Loading Personal Finance Dashboard…</div>;
  }

  const title = NAV.find((n) => n.id === tab)?.label || "Personal Finance Dashboard";

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary">
        <div className="brand">
          <div className="brand-mark" aria-hidden>P</div>
          <div className="brand-name">Personal Finance Dashboard</div>
        </div>
        <nav className="nav-list">
          {NAV.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                className={`nav-item ${tab === item.id ? "active" : ""}`}
                onClick={() => setTab(item.id)}
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <div className="mobile-top">
        <div className="brand">
          <div className="brand-mark" aria-hidden>P</div>
          <div className="brand-name">Personal Finance Dashboard</div>
        </div>
      </div>

      <header className="topbar">
        <h1 className="page-title">{title}</h1>
        <div className="top-actions">
          <button type="button" className="btn btn-ghost" onClick={() => setDriveOpen(true)}>
            <HardDrive size={16} /> Drive sync
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => setImportOpen(true)}>
            <Upload size={16} /> Import
          </button>
          <button type="button" className="btn btn-primary" onClick={() => setAddOpen(true)}>
            <Plus size={16} /> Add entry
          </button>
        </div>
      </header>

      <main className="main">
        {tab === "dashboard" && (
          <DashboardPage
            state={state}
            onPeriodChange={onPeriodChange}
            onNavigate={(t) => setTab(t as TabId)}
            savingPeriod={savingPeriod}
          />
        )}
        {tab === "transactions" && (
          <TransactionsPage
            state={state}
            onPeriodChange={onPeriodChange}
            onRefresh={async () => { await refresh(); }}
            savingPeriod={savingPeriod}
            toast={showToast}
          />
        )}
        {tab === "recurring" && (
          <RecurringPage state={state} onRefresh={async () => { await refresh(); }} toast={showToast} />
        )}
        {tab === "subscriptions" && (
          <SubscriptionsPage state={state} onRefresh={async () => { await refresh(); }} toast={showToast} />
        )}
        {tab === "budgets" && (
          <BudgetsPage state={state} onRefresh={async () => { await refresh(); }} toast={showToast} />
        )}
        {tab === "goals" && (
          <GoalsPage state={state} onRefresh={async () => { await refresh(); }} toast={showToast} />
        )}
        {tab === "documents" && (
          <DocumentsPage
            state={state}
            onRefresh={async () => { await refresh(); }}
            toast={showToast}
            onImportClick={() => setImportOpen(true)}
          />
        )}
        {tab === "rules" && (
          <RulesPage state={state} onRefresh={async () => { await refresh(); }} toast={showToast} />
        )}
        {tab === "settings" && (
          <SettingsPage state={state} onRefresh={async () => { await refresh(); }} toast={showToast} />
        )}
      </main>

      <nav className="bottom-nav" aria-label="Mobile">
        {NAV.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              className={tab === item.id ? "active" : ""}
              onClick={() => setTab(item.id)}
            >
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>

      {toast ? (
        <div className={`toast ${toast.error ? "error" : ""}`} role="status">
          {toast.msg}
        </div>
      ) : null}

      <AddEntryModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        state={state}
        onRefresh={async () => { await refresh(); }}
        toast={showToast}
      />
      <ImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onRefresh={async () => { await refresh(); }}
        toast={showToast}
      />
      <DriveSyncModal
        open={driveOpen}
        onClose={() => setDriveOpen(false)}
        state={state}
        onRefresh={async () => { await refresh(); }}
        toast={showToast}
      />
    </div>
  );
}

function AddEntryModal({
  open,
  onClose,
  state,
  onRefresh,
  toast,
}: {
  open: boolean;
  onClose: () => void;
  state: AppState;
  onRefresh: () => Promise<void>;
  toast: (msg: string, error?: boolean) => void;
}) {
  const [type, setType] = useState<TxType>("expense");
  const [amount, setAmount] = useState("");
  const [merchant, setMerchant] = useState("");
  const [date, setDate] = useState(todayISO());
  const [category, setCategory] = useState("Needs review");
  const [account, setAccount] = useState(state.settings.accounts[0] || "");
  const [tags, setTags] = useState("");
  const [hasReceipt, setHasReceipt] = useState(false);
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setType("expense");
      setAmount("");
      setMerchant("");
      setDate(todayISO());
      setCategory("Needs review");
      setAccount(state.settings.accounts[0] || "");
      setTags("");
      setHasReceipt(false);
      setReceiptFile(null);
    }
  }, [open, state.settings.accounts]);

  async function submit() {
    const amt = Number(amount);
    if (!merchant.trim() || !(amt > 0)) {
      toast("Merchant and a positive amount are required", true);
      return;
    }
    if (!account) {
      toast("Add an account in Settings first", true);
      return;
    }
    setSaving(true);
    try {
      const tagList = tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const result = await createTransaction({
        type,
        amount: amt,
        merchant: merchant.trim(),
        date,
        category,
        account,
        tags: tagList,
        receipt: hasReceipt,
        source: "manual",
      });
      if (result.duplicates) {
        toast("That entry already exists (duplicate)", true);
        return;
      }
      if (hasReceipt && receiptFile) {
        const form = new FormData();
        form.append("file", receiptFile);
        await fetch("/api/documents", { method: "POST", body: form });
      }
      onClose();
      await onRefresh();
      toast("Entry saved");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Add entry" open={open} onClose={onClose}>
      <div className="stack">
        <div className="segmented" role="group" aria-label="Entry type">
          <button type="button" className={type === "expense" ? "active" : ""} onClick={() => setType("expense")}>
            Expense
          </button>
          <button type="button" className={type === "income" ? "active" : ""} onClick={() => setType("income")}>
            Income
          </button>
        </div>
        <div className="field">
          <label htmlFor="amt">Amount</label>
          <input id="amt" className="control" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="" />
        </div>
        <div className="field">
          <label htmlFor="merchant">Merchant or source</label>
          <input id="merchant" className="control" value={merchant} onChange={(e) => setMerchant(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="date">Date</label>
          <input id="date" type="date" className="control" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="cat">Category</label>
          <select id="cat" className="control" value={category} onChange={(e) => setCategory(e.target.value)}>
            {state.settings.categories.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="acc">Account</label>
          {state.settings.accounts.length === 0 ? (
            <button type="button" className="btn btn-ghost" onClick={onClose}>Add an account in Settings</button>
          ) : (
            <select id="acc" className="control" value={account} onChange={(e) => setAccount(e.target.value)}>
              {state.settings.accounts.map((a) => <option key={a}>{a}</option>)}
            </select>
          )}
        </div>
        <div className="field">
          <label htmlFor="tags">Tags (comma separated)</label>
          <input id="tags" className="control" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="Optional" />
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 8, minHeight: 44 }}>
          <input type="checkbox" checked={hasReceipt} onChange={(e) => setHasReceipt(e.target.checked)} />
          I have a receipt to attach
        </label>
        {hasReceipt ? (
          <div className="field">
            <label htmlFor="receipt">Receipt file</label>
            <input id="receipt" type="file" onChange={(e) => setReceiptFile(e.target.files?.[0] || null)} />
          </div>
        ) : null}
      </div>
      <div className="modal-actions">
        <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button type="button" className="btn btn-primary" disabled={saving || !state.settings.accounts.length} onClick={submit}>
          {saving ? "Saving…" : "Save entry"}
        </button>
      </div>
    </Modal>
  );
}

function ImportModal({
  open,
  onClose,
  onRefresh,
  toast,
}: {
  open: boolean;
  onClose: () => void;
  onRefresh: () => Promise<void>;
  toast: (msg: string, error?: boolean) => void;
}) {
  const [text, setText] = useState("");
  const [headers, setHeaders] = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<string[][]>([]);
  const [needsMapping, setNeedsMapping] = useState(false);
  const [mapping, setMapping] = useState<Record<string, number | "">>({});
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setText("");
      setHeaders([]);
      setPreviewRows([]);
      setNeedsMapping(false);
      setMapping({});
      setResult(null);
    }
  }, [open]);

  async function onFile(file: File | null) {
    if (!file) return;
    const content = await file.text();
    setText(content);
    setResult(null);
    const res = await fetch("/api/import/csv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: content, previewOnly: true }),
    });
    const data = await res.json();
    if (data.needsMapping) {
      setNeedsMapping(true);
      setHeaders(data.headers || []);
      setPreviewRows(data.previewRows || []);
      setMapping({
        date: data.mapping?.date ?? "",
        merchant: data.mapping?.merchant ?? "",
        amount: data.mapping?.amount ?? "",
        debit: data.mapping?.debit ?? "",
        credit: data.mapping?.credit ?? "",
        category: data.mapping?.category ?? "",
        account: data.mapping?.account ?? "",
      });
      return;
    }
    if (!res.ok) {
      toast(data.error || "Could not preview CSV", true);
      return;
    }
    setNeedsMapping(false);
    setHeaders(data.headers || []);
    setPreviewRows(data.previewRows || []);
    setMapping(data.mapping || {});
    setResult(`Ready to import ${data.rowCount} rows (${data.skipped} skipped, ${data.needsReview} needs review).`);
  }

  async function runImport() {
    if (!text) {
      toast("Choose a CSV first", true);
      return;
    }
    setSaving(true);
    try {
      const body: Record<string, unknown> = { text };
      if (needsMapping) {
        const cleaned: Record<string, number> = {};
        for (const [k, v] of Object.entries(mapping)) {
          if (v === "" || v === undefined || v === null) continue;
          cleaned[k] = Number(v);
        }
        body.mapping = cleaned;
      }
      const res = await fetch("/api/import/csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.needsMapping) {
        setNeedsMapping(true);
        setHeaders(data.headers || []);
        setPreviewRows(data.previewRows || []);
        toast("Map the CSV columns to continue", true);
        return;
      }
      if (!res.ok) throw new Error(data.error || "Import failed");
      setResult(
        `Inserted ${data.inserted}, duplicates ${data.duplicates}, skipped ${data.skipped}, needs review ${data.needsReview}`
      );
      await onRefresh();
      toast("CSV import complete");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Import failed", true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Import" open={open} onClose={onClose} wide>
      <div className="stack">
        <p className="section-sub" style={{ margin: 0 }}>
          Import a CSV bank or card statement. Documents can also be uploaded from the Documents page.
        </p>
        <div className="field">
          <label htmlFor="csv">CSV file</label>
          <input id="csv" type="file" accept=".csv,text/csv" onChange={(e) => onFile(e.target.files?.[0] || null)} />
        </div>
        {headers.length > 0 ? (
          <div>
            <div className="helper" style={{ marginBottom: 8 }}>Detected columns: {headers.join(", ")}</div>
            {previewRows.length > 0 ? (
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, i) => (
                      <tr key={i}>{headers.map((_, j) => <td key={j}>{row[j]}</td>)}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}
        {needsMapping ? (
          <div className="stack">
            <p className="helper">Mapping is ambiguous — choose columns explicitly.</p>
            {(["date", "merchant", "amount", "debit", "credit", "category", "account"] as const).map((field) => (
              <div className="field" key={field}>
                <label htmlFor={`map-${field}`}>{field}</label>
                <select
                  id={`map-${field}`}
                  className="control"
                  value={mapping[field] === undefined || mapping[field] === "" ? "" : String(mapping[field])}
                  onChange={(e) =>
                    setMapping({
                      ...mapping,
                      [field]: e.target.value === "" ? "" : Number(e.target.value),
                    })
                  }
                >
                  <option value="">—</option>
                  {headers.map((h, i) => (
                    <option key={h + i} value={i}>{h}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        ) : null}
        {result ? <div className="navy-panel">{result}</div> : null}
      </div>
      <div className="modal-actions">
        <button type="button" className="btn btn-ghost" onClick={onClose}>Close</button>
        <button type="button" className="btn btn-primary" disabled={saving || !text} onClick={runImport}>
          {saving ? "Importing…" : "Import CSV"}
        </button>
      </div>
    </Modal>
  );
}
