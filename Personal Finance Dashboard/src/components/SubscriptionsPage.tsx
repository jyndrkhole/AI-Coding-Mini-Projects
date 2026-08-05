"use client";

import { useMemo, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import type { AppState, Cadence, SubscriptionItem } from "@/lib/types";
import { detectPatterns, monthlyEquivalent } from "@/lib/detection";
import { formatMoney, savePreferences, todayISO } from "@/lib/client";
import { Modal } from "./Modal";

const CADENCES: Cadence[] = ["weekly", "biweekly", "monthly", "quarterly", "annual"];

export function SubscriptionsPage({
  state,
  onRefresh,
  toast,
}: {
  state: AppState;
  onRefresh: () => Promise<void>;
  toast: (msg: string, error?: boolean) => void;
}) {
  const suggestions = useMemo(
    () =>
      detectPatterns(state.transactions, state.settings.dismissedPatterns).filter(
        (s) => s.kind === "subscription"
      ),
    [state]
  );
  const confirmed = state.settings.subscriptions;
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<SubscriptionItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    category: "Subscriptions",
    amount: "",
    cadence: "monthly" as Cadence,
    nextDate: todayISO(),
    account: "",
    active: true,
  });

  const confirmedKeys = new Set(
    confirmed.map((c) => `subscription:${c.name.toLowerCase()}:${c.cadence}`)
  );
  const visibleSuggestions = suggestions.filter((s) => !confirmedKeys.has(s.key));
  const monthly =
    confirmed.filter((c) => c.active).reduce((s, c) => s + monthlyEquivalent(c.amount, c.cadence), 0) +
    visibleSuggestions.reduce((s, c) => s + c.monthlyEquivalent, 0);
  const next = [...confirmed.filter((c) => c.active)].sort((a, b) =>
    a.nextDate.localeCompare(b.nextDate)
  )[0];

  function openAdd() {
    setEditing(null);
    setForm({
      name: "",
      category: "Subscriptions",
      amount: "",
      cadence: "monthly",
      nextDate: todayISO(),
      account: state.settings.accounts[0] || "",
      active: true,
    });
    setOpen(true);
  }

  function openEdit(item: SubscriptionItem) {
    setEditing(item);
    setForm({
      name: item.name,
      category: item.category,
      amount: String(item.amount),
      cadence: item.cadence,
      nextDate: item.nextDate,
      account: item.account || "",
      active: item.active,
    });
    setOpen(true);
  }

  async function save() {
    const amount = Number(form.amount);
    if (!form.name.trim() || !(amount > 0)) {
      toast("Service name and positive amount are required", true);
      return;
    }
    setSaving(true);
    try {
      const item: SubscriptionItem = {
        id: editing?.id || uuidv4(),
        name: form.name.trim(),
        category: form.category,
        amount,
        cadence: form.cadence,
        nextDate: form.nextDate,
        account: form.account || undefined,
        active: form.active,
      };
      const subscriptions = editing
        ? confirmed.map((c) => (c.id === editing.id ? item : c))
        : [...confirmed, item];
      await savePreferences({ subscriptions });
      setOpen(false);
      await onRefresh();
      toast(editing ? "Subscription updated" : "Subscription added");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", true);
    } finally {
      setSaving(false);
    }
  }

  async function keepSuggestion(key: string) {
    const s = suggestions.find((x) => x.key === key);
    if (!s) return;
    const item: SubscriptionItem = {
      id: uuidv4(),
      name: s.displayMerchant,
      category: s.category,
      amount: s.averageAmount,
      cadence: s.cadence,
      nextDate: s.nextDate,
      active: true,
    };
    await savePreferences({ subscriptions: [...confirmed, item] });
    await onRefresh();
    toast("Kept as subscription");
  }

  async function ignoreSuggestion(key: string) {
    await savePreferences({
      dismissedPatterns: [...state.settings.dismissedPatterns, key],
    });
    await onRefresh();
    toast("Suggestion ignored");
  }

  async function remove(id: string) {
    await savePreferences({ subscriptions: confirmed.filter((c) => c.id !== id) });
    await onRefresh();
    toast("Removed");
  }

  return (
    <div className="stack">
      <div className="summary-grid" style={{ gridTemplateColumns: "repeat(3, minmax(0,1fr))" }}>
        <div className="card summary-card">
          <div className="summary-label">Monthly subscriptions</div>
          <div className="summary-value">{formatMoney(monthly)}</div>
          <div className="summary-strip">Confirmed + visible suggestions</div>
        </div>
        <div className="card summary-card">
          <div className="summary-label">Annual equivalent</div>
          <div className="summary-value">{formatMoney(monthly * 12)}</div>
          <div className="summary-strip">Monthly × 12</div>
        </div>
        <div className="card summary-card">
          <div className="summary-label">Next renewal</div>
          <div className="summary-value" style={{ fontSize: 22 }}>
            {next ? next.nextDate : "—"}
          </div>
          <div className="summary-strip">{next ? next.name : "No confirmed subscriptions"}</div>
        </div>
      </div>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <h3 className="section-title">Confirmed subscriptions</h3>
            <p className="section-sub">Services you have kept or added manually.</p>
          </div>
          <button type="button" className="btn btn-primary" onClick={openAdd}>Add subscription</button>
        </div>
        {confirmed.length === 0 ? (
          <div className="empty-state">No subscriptions yet.</div>
        ) : (
          <div className="stack">
            {confirmed.map((item) => (
              <div key={item.id} className="card" style={{ boxShadow: "none" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{item.name}</div>
                    <div className="helper">
                      {item.category} · {item.cadence} · renews {item.nextDate}
                      {item.active ? "" : " · inactive"}
                    </div>
                  </div>
                  <div className="row-actions">
                    <div className="amount-expense">{formatMoney(item.amount)}</div>
                    <button type="button" className="btn btn-ghost" onClick={() => openEdit(item)}>Edit</button>
                    <button type="button" className="btn btn-ghost" onClick={() => remove(item.id)}>Delete</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="section-title">Subscription suggestions</h3>
        <p className="section-sub">Stable patterns that look like subscriptions.</p>
        {visibleSuggestions.length === 0 ? (
          <div className="empty-state">No subscription suggestions right now.</div>
        ) : (
          <div className="stack">
            {visibleSuggestions.map((s) => (
              <div key={s.key} style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontWeight: 700 }}>{s.displayMerchant}</div>
                  <div className="helper">
                    {s.category} · {s.cadence} · {s.occurrenceCount} occurrences · {s.confidence} · next {s.nextDate}
                  </div>
                </div>
                <div className="row-actions">
                  <span>{formatMoney(s.averageAmount)} · ~{formatMoney(s.monthlyEquivalent)}/mo</span>
                  <button type="button" className="btn btn-primary" onClick={() => keepSuggestion(s.key)}>Keep</button>
                  <button type="button" className="btn btn-ghost" onClick={() => ignoreSuggestion(s.key)}>Ignore</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <Modal title={editing ? "Edit subscription" : "Add subscription"} open={open} onClose={() => setOpen(false)}>
        <div className="stack">
          <div className="field">
            <label htmlFor="s-name">Service name</label>
            <input id="s-name" className="control" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="s-cat">Group / category</label>
            <select id="s-cat" className="control" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {state.settings.categories.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="s-amt">Amount</label>
            <input id="s-amt" className="control" inputMode="decimal" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="s-cad">Cadence</label>
            <select id="s-cad" className="control" value={form.cadence} onChange={(e) => setForm({ ...form, cadence: e.target.value as Cadence })}>
              {CADENCES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="s-next">Next renewal</label>
            <input id="s-next" type="date" className="control" value={form.nextDate} onChange={(e) => setForm({ ...form, nextDate: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="s-acc">Account (optional)</label>
            <select id="s-acc" className="control" value={form.account} onChange={(e) => setForm({ ...form, account: e.target.value })}>
              <option value="">None</option>
              {state.settings.accounts.map((a) => <option key={a}>{a}</option>)}
            </select>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, minHeight: 44 }}>
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
            Active
          </label>
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button>
          <button type="button" className="btn btn-primary" disabled={saving} onClick={save}>{saving ? "Saving…" : "Save"}</button>
        </div>
      </Modal>
    </div>
  );
}
