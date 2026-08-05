"use client";

import { useMemo, useState } from "react";
import type { AppState, Rule } from "@/lib/types";
import { Modal } from "./Modal";

export function RulesPage({
  state,
  onRefresh,
  toast,
}: {
  state: AppState;
  onRefresh: () => Promise<void>;
  toast: (msg: string, error?: boolean) => void;
}) {
  const [ruleOpen, setRuleOpen] = useState(false);
  const [tagOpen, setTagOpen] = useState(false);
  const [editing, setEditing] = useState<Rule | null>(null);
  const [saving, setSaving] = useState(false);
  const [whenText, setWhenText] = useState("");
  const [thenText, setThenText] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [tagName, setTagName] = useState("");

  const usage = useMemo(() => {
    const map = new Map<string, number>();
    for (const t of state.transactions) {
      for (const tag of t.tags) {
        map.set(tag.toLowerCase(), (map.get(tag.toLowerCase()) || 0) + 1);
      }
    }
    return map;
  }, [state.transactions]);

  function openCreate() {
    setEditing(null);
    setWhenText("");
    setThenText("");
    setEnabled(true);
    setRuleOpen(true);
  }

  function openEdit(rule: Rule) {
    setEditing(rule);
    setWhenText(rule.whenText);
    setThenText(rule.thenText);
    setEnabled(rule.enabled);
    setRuleOpen(true);
  }

  async function saveRule() {
    if (!whenText.trim() || !thenText.trim()) {
      toast("Both when and then are required", true);
      return;
    }
    setSaving(true);
    try {
      const res = await fetch("/api/rules", {
        method: editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          editing
            ? { id: editing.id, whenText, thenText, enabled }
            : { whenText, thenText, enabled }
        ),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Save failed");
      setRuleOpen(false);
      await onRefresh();
      toast(editing ? "Rule updated" : "Rule created");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", true);
    } finally {
      setSaving(false);
    }
  }

  async function toggleRule(rule: Rule) {
    const res = await fetch("/api/rules", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: rule.id, enabled: !rule.enabled }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      toast(data.error || "Toggle failed", true);
      return;
    }
    await onRefresh();
  }

  async function deleteRule(id: string) {
    const res = await fetch(`/api/rules?id=${encodeURIComponent(id)}`, { method: "DELETE" });
    if (!res.ok) {
      toast("Delete failed", true);
      return;
    }
    await onRefresh();
    toast("Rule deleted");
  }

  async function createTag() {
    if (!tagName.trim()) {
      toast("Enter a tag name", true);
      return;
    }
    setSaving(true);
    try {
      const res = await fetch("/api/tags", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: tagName.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Create failed");
      setTagOpen(false);
      setTagName("");
      await onRefresh();
      toast("Tag created");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Create failed", true);
    } finally {
      setSaving(false);
    }
  }

  async function deleteTag(name: string) {
    const used = usage.get(name.toLowerCase()) || 0;
    let strip = false;
    if (used > 0) {
      const ok = window.confirm(
        `"${name}" is used on ${used} transaction(s). Remove it from historical transactions too?`
      );
      strip = ok;
      if (!ok) {
        const keep = window.confirm("Delete the tag definition only (keep historical labels)?");
        if (!keep) return;
      }
    } else if (!window.confirm(`Delete tag "${name}"?`)) {
      return;
    }
    const res = await fetch(
      `/api/tags?name=${encodeURIComponent(name)}${strip ? "&strip=1" : ""}`,
      { method: "DELETE" }
    );
    if (!res.ok) {
      toast("Delete failed", true);
      return;
    }
    await onRefresh();
    toast("Tag deleted");
  }

  return (
    <div className="stack">
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <h3 className="section-title">Categorization rules</h3>
            <p className="section-sub">Applied to future imports after duplicate detection.</p>
          </div>
          <button type="button" className="btn btn-primary" onClick={openCreate}>Create rule</button>
        </div>
        {state.rules.length === 0 ? (
          <div className="empty-state">No rules yet.</div>
        ) : (
          <div className="stack">
            {state.rules.map((rule) => (
              <div key={rule.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                <div>
                  <div>
                    When <strong>{rule.whenText}</strong> then <strong>{rule.thenText}</strong>
                  </div>
                </div>
                <div className="row-actions">
                  <label style={{ display: "flex", alignItems: "center", gap: 8, minHeight: 44 }}>
                    <input type="checkbox" checked={rule.enabled} onChange={() => toggleRule(rule)} />
                    Enabled
                  </label>
                  <button type="button" className="btn btn-ghost" onClick={() => openEdit(rule)}>Edit</button>
                  <button type="button" className="btn btn-ghost" onClick={() => deleteRule(rule.id)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <h3 className="section-title">Tags</h3>
            <p className="section-sub">Create a tag with a name only — no category required.</p>
          </div>
          <button type="button" className="btn btn-primary" onClick={() => setTagOpen(true)}>Create tag</button>
        </div>
        {state.tags.length === 0 ? (
          <div className="empty-state">No tags yet.</div>
        ) : (
          <div className="stack">
            {state.tags.map((t) => (
              <div key={t.name} style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
                <div>
                  <span className="pill">{t.name}</span>
                  <span className="helper" style={{ marginLeft: 8 }}>
                    used {usage.get(t.name.toLowerCase()) || 0}×
                  </span>
                </div>
                <button type="button" className="btn btn-ghost" onClick={() => deleteTag(t.name)}>Delete</button>
              </div>
            ))}
          </div>
        )}
      </div>

      <Modal title={editing ? "Edit rule" : "Create rule"} open={ruleOpen} onClose={() => setRuleOpen(false)}>
        <div className="stack">
          <div className="field">
            <label htmlFor="when">When (merchant/source contains)</label>
            <input id="when" className="control" value={whenText} onChange={(e) => setWhenText(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="then">Then (category name, or category: X / tag: Y)</label>
            <input id="then" className="control" value={thenText} onChange={(e) => setThenText(e.target.value)} />
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, minHeight: 44 }}>
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
            Enabled
          </label>
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={() => setRuleOpen(false)}>Cancel</button>
          <button type="button" className="btn btn-primary" disabled={saving} onClick={saveRule}>{saving ? "Saving…" : "Save"}</button>
        </div>
      </Modal>

      <Modal title="Create tag" open={tagOpen} onClose={() => setTagOpen(false)}>
        <div className="field">
          <label htmlFor="tag-only">Tag name</label>
          <input id="tag-only" className="control" value={tagName} onChange={(e) => setTagName(e.target.value)} placeholder="Name only" />
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={() => setTagOpen(false)}>Cancel</button>
          <button type="button" className="btn btn-primary" disabled={saving} onClick={createTag}>{saving ? "Saving…" : "Create"}</button>
        </div>
      </Modal>
    </div>
  );
}
