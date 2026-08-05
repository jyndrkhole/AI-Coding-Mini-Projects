"use client";

import { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import type { AppState, Budget } from "@/lib/types";
import { formatMoney, savePreferences } from "@/lib/client";
import { toISODate } from "@/lib/periods";
import { Modal } from "./Modal";

function currentMonthKey(now = new Date()) {
  return toISODate(new Date(now.getFullYear(), now.getMonth(), 1)).slice(0, 7);
}

export function BudgetsPage({
  state,
  onRefresh,
  toast,
}: {
  state: AppState;
  onRefresh: () => Promise<void>;
  toast: (msg: string, error?: boolean) => void;
}) {
  const budgets = state.settings.budgets;
  const month = currentMonthKey();
  const [open, setOpen] = useState(false);
  const [adjustOpen, setAdjustOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ category: "Groceries", limit: "", active: true });

  function spentFor(category: string) {
    return state.transactions
      .filter(
        (t) =>
          t.type === "expense" &&
          t.category === category &&
          t.date.startsWith(month)
      )
      .reduce((s, t) => s + t.amount, 0);
  }

  const active = budgets.filter((b) => b.active);
  const totalLimit = active.reduce((s, b) => s + b.limit, 0);
  const totalSpent = active.reduce((s, b) => s + spentFor(b.category), 0);
  const health = totalLimit === 0 ? 0 : Math.min(100, (totalSpent / totalLimit) * 100);

  async function createBudget() {
    const limit = Number(form.limit);
    if (!(limit > 0)) {
      toast("Enter a positive monthly limit", true);
      return;
    }
    if (budgets.some((b) => b.category.toLowerCase() === form.category.toLowerCase())) {
      toast("A budget for that category already exists", true);
      return;
    }
    setSaving(true);
    try {
      const item: Budget = {
        id: uuidv4(),
        category: form.category,
        limit,
        active: form.active,
      };
      await savePreferences({ budgets: [...budgets, item] });
      setOpen(false);
      setForm({ category: "Groceries", limit: "", active: true });
      await onRefresh();
      toast("Budget created");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", true);
    } finally {
      setSaving(false);
    }
  }

  async function updateBudget(id: string, patch: Partial<Budget>) {
    const next = budgets.map((b) => (b.id === id ? { ...b, ...patch } : b));
    await savePreferences({ budgets: next });
    await onRefresh();
  }

  async function deleteBudget(id: string) {
    await savePreferences({ budgets: budgets.filter((b) => b.id !== id) });
    await onRefresh();
    toast("Budget deleted");
  }

  return (
    <div className="stack">
      <div className="grid-2">
        <div className="card">
          <h3 className="section-title">Budget health</h3>
          <p className="section-sub">This month across active budgets.</p>
          {active.length === 0 ? (
            <div className="empty-state">Create a budget to see health.</div>
          ) : (
            <>
              <div className="summary-value" style={{ marginBottom: 12 }}>
                {health.toFixed(0)}% used
              </div>
              <div className={`progress ${health > 100 ? "over" : ""}`}>
                <span style={{ width: `${Math.min(health, 100)}%` }} />
              </div>
              <div className="helper" style={{ marginTop: 10 }}>
                Spent {formatMoney(totalSpent)} of {formatMoney(totalLimit)}
              </div>
            </>
          )}
        </div>
        <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: 12 }}>
          <button type="button" className="btn btn-primary" onClick={() => setOpen(true)}>
            Create budget
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => setAdjustOpen(true)} disabled={!budgets.length}>
            Adjust budgets
          </button>
        </div>
      </div>

      {budgets.length === 0 ? (
        <div className="card empty-state">No budgets yet. Create one to track monthly spending by category.</div>
      ) : (
        <div className="stack">
          {budgets.map((b) => {
            const spent = spentFor(b.category);
            const remaining = b.limit - spent;
            const pct = b.limit === 0 ? 0 : (spent / b.limit) * 100;
            const over = spent > b.limit;
            return (
              <div key={b.id} className="card">
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{b.category}</div>
                    <div className="helper">{b.active ? "Active" : "Inactive"} · {month}</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div>{formatMoney(spent)} / {formatMoney(b.limit)}</div>
                    <div className="helper" style={{ color: over ? "var(--orange)" : undefined }}>
                      {over ? `Over by ${formatMoney(spent - b.limit)}` : `${formatMoney(remaining)} remaining`}
                    </div>
                  </div>
                </div>
                <div className={`progress ${over ? "over" : ""}`} style={{ marginTop: 12 }}>
                  <span style={{ width: `${Math.min(pct, 100)}%` }} />
                </div>
                <div className="helper" style={{ marginTop: 8 }}>{pct.toFixed(0)}%</div>
              </div>
            );
          })}
        </div>
      )}

      <Modal title="Create budget" open={open} onClose={() => setOpen(false)}>
        <div className="stack">
          <div className="field">
            <label htmlFor="b-cat">Category</label>
            <select id="b-cat" className="control" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {state.settings.categories.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="b-limit">Monthly limit</label>
            <input id="b-limit" className="control" inputMode="decimal" value={form.limit} onChange={(e) => setForm({ ...form, limit: e.target.value })} />
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, minHeight: 44 }}>
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
            Active
          </label>
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button>
          <button type="button" className="btn btn-primary" disabled={saving} onClick={createBudget}>{saving ? "Saving…" : "Create"}</button>
        </div>
      </Modal>

      <Modal title="Adjust budgets" open={adjustOpen} onClose={() => setAdjustOpen(false)} wide>
        {budgets.length === 0 ? (
          <div className="empty-state">No budgets to adjust.</div>
        ) : (
          <div className="stack">
            {budgets.map((b) => (
              <div key={b.id} className="card" style={{ boxShadow: "none" }}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>{b.category}</div>
                <div className="filters">
                  <div className="field" style={{ minWidth: 120 }}>
                    <label>Limit</label>
                    <input
                      className="control"
                      defaultValue={b.limit}
                      onBlur={(e) => {
                        const limit = Number(e.target.value);
                        if (limit > 0) updateBudget(b.id, { limit });
                      }}
                    />
                  </div>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, minHeight: 44 }}>
                    <input
                      type="checkbox"
                      checked={b.active}
                      onChange={(e) => updateBudget(b.id, { active: e.target.checked })}
                    />
                    Active
                  </label>
                  <button type="button" className="btn btn-ghost" onClick={() => deleteBudget(b.id)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="modal-actions">
          <button type="button" className="btn btn-primary" onClick={() => setAdjustOpen(false)}>Done</button>
        </div>
      </Modal>
    </div>
  );
}
