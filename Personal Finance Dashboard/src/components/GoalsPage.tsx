"use client";

import { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import type { AppState, Goal } from "@/lib/types";
import { formatMoney, savePreferences } from "@/lib/client";
import { Modal } from "./Modal";

export function GoalsPage({
  state,
  onRefresh,
  toast,
}: {
  state: AppState;
  onRefresh: () => Promise<void>;
  toast: (msg: string, error?: boolean) => void;
}) {
  const goals = state.settings.goals;
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Goal | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    target: "",
    current: "",
    dueDate: "",
    note: "",
  });

  function openAdd() {
    setEditing(null);
    setForm({ name: "", target: "", current: "", dueDate: "", note: "" });
    setOpen(true);
  }

  function openEdit(g: Goal) {
    setEditing(g);
    setForm({
      name: g.name,
      target: String(g.target),
      current: String(g.current),
      dueDate: g.dueDate || "",
      note: g.note || "",
    });
    setOpen(true);
  }

  async function save() {
    const target = Number(form.target);
    const current = Number(form.current || 0);
    if (!form.name.trim() || !(target > 0) || current < 0 || !Number.isFinite(current)) {
      toast("Name and a positive target are required", true);
      return;
    }
    setSaving(true);
    try {
      const item: Goal = {
        id: editing?.id || uuidv4(),
        name: form.name.trim(),
        target,
        current,
        dueDate: form.dueDate || undefined,
        note: form.note.trim() || undefined,
      };
      const next = editing
        ? goals.map((g) => (g.id === editing.id ? item : g))
        : [...goals, item];
      await savePreferences({ goals: next });
      setOpen(false);
      await onRefresh();
      toast(editing ? "Goal updated" : "Goal created");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", true);
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    await savePreferences({ goals: goals.filter((g) => g.id !== id) });
    await onRefresh();
    toast("Goal deleted");
  }

  return (
    <div className="stack">
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button type="button" className="btn btn-primary" onClick={openAdd}>
          Create goal
        </button>
      </div>

      {goals.length === 0 ? (
        <div className="card empty-state">No goals yet. Create a savings goal to track progress.</div>
      ) : (
        <div className="summary-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))" }}>
          {goals.map((g) => {
            const remaining = Math.max(0, g.target - g.current);
            const pct = g.target === 0 ? 0 : Math.min(100, (g.current / g.target) * 100);
            return (
              <div key={g.id} className="card">
                <div style={{ fontWeight: 700, fontSize: 16 }}>{g.name}</div>
                <div className="helper" style={{ marginBottom: 12 }}>
                  {g.dueDate ? `Due ${g.dueDate}` : "No due date"}
                </div>
                <div>{formatMoney(g.current)} of {formatMoney(g.target)}</div>
                <div className="helper">{formatMoney(remaining)} remaining</div>
                <div className="progress" style={{ marginTop: 12 }}>
                  <span style={{ width: `${pct}%` }} />
                </div>
                <div className="helper" style={{ marginTop: 8 }}>{pct.toFixed(0)}%</div>
                {g.note ? <p className="helper">{g.note}</p> : null}
                <div className="row-actions" style={{ marginTop: 12 }}>
                  <button type="button" className="btn btn-ghost" onClick={() => openEdit(g)}>Edit</button>
                  <button type="button" className="btn btn-ghost" onClick={() => remove(g.id)}>Delete</button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Modal title={editing ? "Edit goal" : "Add goal"} open={open} onClose={() => setOpen(false)}>
        <div className="stack">
          <div className="field">
            <label htmlFor="g-name">Name</label>
            <input id="g-name" className="control" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="g-target">Target amount</label>
            <input id="g-target" className="control" inputMode="decimal" value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="g-current">Current saved</label>
            <input id="g-current" className="control" inputMode="decimal" value={form.current} onChange={(e) => setForm({ ...form, current: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="g-due">Due date (optional)</label>
            <input id="g-due" type="date" className="control" value={form.dueDate} onChange={(e) => setForm({ ...form, dueDate: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="g-note">Note (optional)</label>
            <textarea id="g-note" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
          </div>
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button>
          <button type="button" className="btn btn-primary" disabled={saving} onClick={save}>{saving ? "Saving…" : "Save"}</button>
        </div>
      </Modal>
    </div>
  );
}
