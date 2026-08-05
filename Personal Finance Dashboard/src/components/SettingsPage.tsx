"use client";

import { useState } from "react";
import type { AppState } from "@/lib/types";
import { DEFAULT_TIMEZONE, WIPE_CONFIRMATION } from "@/lib/types";
import {
  CURRENCY_OPTIONS,
  detectCurrencyFromLocation,
  formatMoney,
  savePreferences,
} from "@/lib/client";
import { localeForCurrency } from "@/lib/currency";
import { Modal } from "./Modal";

export function SettingsPage({
  state,
  onRefresh,
  toast,
  formLockedNames,
}: {
  state: AppState;
  onRefresh: () => Promise<void>;
  toast: (msg: string, error?: boolean) => void;
  formLockedNames?: { categories: string[]; accounts: string[] };
}) {
  const [assets, setAssets] = useState(String(state.settings.assetsTotal || ""));
  const [liabilities, setLiabilities] = useState(String(state.settings.liabilitiesTotal || ""));
  const [saving, setSaving] = useState(false);
  const [newCategory, setNewCategory] = useState("");
  const [newAccount, setNewAccount] = useState("");
  const [newTag, setNewTag] = useState("");
  const [wipeOpen, setWipeOpen] = useState(false);
  const [wipeText, setWipeText] = useState("");

  const preview =
    (Number(assets) || 0) - (Number(liabilities) || 0);

  async function saveCurrency(code: string) {
    setSaving(true);
    try {
      await savePreferences({
        currency: code,
        locale: localeForCurrency(code),
      });
      await onRefresh();
      toast(`Currency set to ${code}`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", true);
    } finally {
      setSaving(false);
    }
  }

  async function useLocationCurrency() {
    const detected = detectCurrencyFromLocation();
    await saveCurrency(detected.currency);
  }

  async function saveNetWorth() {
    const a = Number(assets);
    const l = Number(liabilities);
    if (!Number.isFinite(a) || a < 0 || !Number.isFinite(l) || l < 0) {
      toast("Enter valid non-negative totals", true);
      return;
    }
    setSaving(true);
    try {
      await savePreferences({
        assetsTotal: a,
        liabilitiesTotal: l,
        netWorthConfigured: true,
      });
      await onRefresh();
      toast("Net worth saved");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", true);
    } finally {
      setSaving(false);
    }
  }

  async function addName(kind: "categories" | "accounts", value: string) {
    const trimmed = value.trim();
    if (!trimmed) return;
    const list = state.settings[kind];
    if (list.some((x) => x.toLowerCase() === trimmed.toLowerCase())) {
      toast("That name already exists", true);
      return;
    }
    await savePreferences({ [kind]: [...list, trimmed] });
    await onRefresh();
    toast(`${kind === "categories" ? "Category" : "Account"} added`);
  }

  async function removeName(kind: "categories" | "accounts", value: string) {
    const locked = formLockedNames?.[kind] || [];
    if (locked.some((x) => x.toLowerCase() === value.toLowerCase())) {
      toast(`Cannot delete "${value}" while it is used in an open form`, true);
      return;
    }
    if (!window.confirm(`Remove "${value}" from future pickers? Historical labels stay on past transactions.`)) {
      return;
    }
    await savePreferences({
      [kind]: state.settings[kind].filter((x) => x !== value),
    });
    await onRefresh();
    toast("Removed");
  }

  async function addTag() {
    if (!newTag.trim()) return;
    const res = await fetch("/api/tags", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newTag.trim() }),
    });
    if (!res.ok) {
      toast("Failed to add tag", true);
      return;
    }
    setNewTag("");
    await onRefresh();
    toast("Tag added");
  }

  async function restoreIgnored() {
    await savePreferences({ dismissedPatterns: [] });
    await onRefresh();
    toast("Ignored suggestions restored");
  }

  async function wipe() {
    setSaving(true);
    try {
      const res = await fetch("/api/state", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: WIPE_CONFIRMATION }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Wipe failed");
      setWipeOpen(false);
      setWipeText("");
      await onRefresh();
      toast("All Ledgerly data erased");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Wipe failed", true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack">
      <div className="card">
        <h3 className="section-title">Currency</h3>
        <p className="section-sub">
          Amounts display in your selected currency. Default is ₹ INR (India). You can also match your device location.
        </p>
        <div className="field" style={{ maxWidth: 360 }}>
          <label htmlFor="currency">Display currency</label>
          <select
            id="currency"
            className="control"
            value={state.settings.currency || "INR"}
            disabled={saving}
            onChange={(e) => saveCurrency(e.target.value)}
          >
            {CURRENCY_OPTIONS.map((c) => (
              <option key={c.code} value={c.code}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
        <div className="helper" style={{ marginTop: 10 }}>
          Preview: {formatMoney(1234.56, state.settings.currency, state.settings.locale)}
        </div>
        <button
          type="button"
          className="btn btn-ghost"
          style={{ marginTop: 12 }}
          disabled={saving}
          onClick={useLocationCurrency}
        >
          Use location default
        </button>
      </div>

      <div className="card">
        <h3 className="section-title">Net worth setup</h3>
        <p className="section-sub">
          Net Worth is your assets minus liabilities — not monthly income minus expenses.
        </p>
        <div className="filters">
          <div className="field" style={{ minWidth: 160 }}>
            <label htmlFor="assets">Total assets</label>
            <input id="assets" className="control" inputMode="decimal" value={assets} onChange={(e) => setAssets(e.target.value)} />
          </div>
          <div className="field" style={{ minWidth: 160 }}>
            <label htmlFor="liab">Total liabilities</label>
            <input id="liab" className="control" inputMode="decimal" value={liabilities} onChange={(e) => setLiabilities(e.target.value)} />
          </div>
        </div>
        <div className="helper" style={{ marginBottom: 12 }}>
          Live preview: {formatMoney(preview)}
        </div>
        <button type="button" className="btn btn-primary" disabled={saving} onClick={saveNetWorth}>
          {saving ? "Saving…" : "Save net worth"}
        </button>
      </div>

      <div className="card">
        <h3 className="section-title">Managed categories</h3>
        <div className="filters">
          <div className="field" style={{ flex: 1 }}>
            <label htmlFor="new-cat">Add category</label>
            <input id="new-cat" className="control" value={newCategory} onChange={(e) => setNewCategory(e.target.value)} />
          </div>
          <button type="button" className="btn btn-primary" style={{ alignSelf: "end" }} onClick={() => { addName("categories", newCategory); setNewCategory(""); }}>Add</button>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
          {state.settings.categories.map((c) => (
            <span className="pill" key={c}>
              {c}
              <button type="button" aria-label={`Remove ${c}`} onClick={() => removeName("categories", c)}>×</button>
            </span>
          ))}
        </div>
      </div>

      <div className="card">
        <h3 className="section-title">Managed accounts</h3>
        <div className="filters">
          <div className="field" style={{ flex: 1 }}>
            <label htmlFor="new-acc">Add account</label>
            <input id="new-acc" className="control" value={newAccount} onChange={(e) => setNewAccount(e.target.value)} />
          </div>
          <button type="button" className="btn btn-primary" style={{ alignSelf: "end" }} onClick={() => { addName("accounts", newAccount); setNewAccount(""); }}>Add</button>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
          {state.settings.accounts.map((a) => (
            <span className="pill" key={a}>
              {a}
              <button type="button" aria-label={`Remove ${a}`} onClick={() => removeName("accounts", a)}>×</button>
            </span>
          ))}
        </div>
      </div>

      <div className="card">
        <h3 className="section-title">Managed tags</h3>
        <div className="filters">
          <div className="field" style={{ flex: 1 }}>
            <label htmlFor="new-tag-set">Add tag (name only)</label>
            <input id="new-tag-set" className="control" value={newTag} onChange={(e) => setNewTag(e.target.value)} />
          </div>
          <button type="button" className="btn btn-primary" style={{ alignSelf: "end" }} onClick={addTag}>Add</button>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
          {state.tags.map((t) => (
            <span className="pill" key={t.name}>{t.name}</span>
          ))}
          {state.tags.length === 0 ? <span className="helper">No tags yet</span> : null}
        </div>
      </div>

      <div className="card">
        <h3 className="section-title">Automatic detection</h3>
        <p className="section-sub">
          Recurring and subscription suggestions come from real expense patterns (cadence windows and amount stability), not from merchant names alone. You must Keep a suggestion before it becomes confirmed.
        </p>
        <p className="helper">{state.settings.dismissedPatterns.length} ignored suggestion(s)</p>
        <button type="button" className="btn btn-ghost" onClick={restoreIgnored}>
          Restore ignored suggestions
        </button>
      </div>

      <div className="card">
        <h3 className="section-title">Google Drive sync</h3>
        <p className="section-sub">
          Add a receipt, CSV, statement, invoice, or supported document to your dedicated folder. It is checked daily at 8:00 AM.
        </p>
        <div className="stack" style={{ gap: 6 }}>
          <div>Folder: {state.settings.driveFolder?.name || "Ledgerly Financial Inbox"}</div>
          {state.settings.driveFolder?.url ? (
            <a href={state.settings.driveFolder.url} target="_blank" rel="noreferrer">Open folder</a>
          ) : null}
          <div className="helper">
            Schedule: {state.settings.driveSync.schedule?.time || "08:00"} daily · {state.settings.driveSync.schedule?.timezone || DEFAULT_TIMEZONE}
          </div>
          <div className="helper">Last sync: {state.settings.driveSync.lastSyncedAt || "—"}</div>
          <div className="helper">
            Status {state.settings.driveSync.status || "idle"} · imported {state.settings.driveSync.imported || 0} · duplicates {state.settings.driveSync.duplicates || 0} · review {state.settings.driveSync.review || 0}
          </div>
          {(state.settings.driveSync.errors || []).length > 0 ? (
            <div className="helper" style={{ color: "var(--danger)" }}>
              {(state.settings.driveSync.errors || []).slice(0, 3).join(" · ")}
            </div>
          ) : null}
        </div>
      </div>

      <div className="card" style={{ borderColor: "#f0c7c7" }}>
        <h3 className="section-title">Danger zone</h3>
        <p className="section-sub">
          Erase all Ledgerly database records and stored file copies. Original Google Drive files remain.
        </p>
        <button type="button" className="btn btn-danger" onClick={() => { setWipeText(""); setWipeOpen(true); }}>
          Erase all Ledgerly data
        </button>
      </div>

      <Modal title="Erase all Ledgerly data" open={wipeOpen} onClose={() => setWipeOpen(false)}>
        <p>
          This deletes Site database records and stored R2 file copies. Original Google Drive files will remain. The daily automation stays configured but will not reimport Drive files modified at or before the new reset timestamp.
        </p>
        <div className="field">
          <label htmlFor="wipe">Type DELETE to confirm</label>
          <input id="wipe" className="control" value={wipeText} onChange={(e) => setWipeText(e.target.value)} autoComplete="off" />
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={() => setWipeOpen(false)}>Cancel</button>
          <button
            type="button"
            className="btn btn-danger"
            disabled={wipeText !== "DELETE" || saving}
            onClick={wipe}
          >
            {saving ? "Erasing…" : "Erase everything"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
