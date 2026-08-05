"use client";

import { useMemo, useState } from "react";
import { Plus, Receipt } from "lucide-react";
import { PERIOD_OPTIONS, type AppState, type PeriodKey, type Transaction } from "@/lib/types";
import { formatMoney, patchTransaction } from "@/lib/client";
import { inPeriod } from "@/lib/periods";
import { Modal } from "./Modal";

export function TransactionsPage({
  state,
  onPeriodChange,
  onRefresh,
  savingPeriod,
  toast,
}: {
  state: AppState;
  onPeriodChange: (p: PeriodKey) => void;
  onRefresh: () => Promise<void>;
  savingPeriod: boolean;
  toast: (msg: string, error?: boolean) => void;
}) {
  const [search, setSearch] = useState("");
  const [account, setAccount] = useState("all");
  const [category, setCategory] = useState("all");
  const [tagTx, setTagTx] = useState<Transaction | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState("");
  const [saving, setSaving] = useState(false);

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return state.transactions
      .filter((t) => inPeriod(t.date, state.settings.selectedPeriod))
      .filter((t) => (account === "all" ? true : t.account === account))
      .filter((t) => (category === "all" ? true : t.category === category))
      .filter((t) => {
        if (!q) return true;
        return (
          t.merchant.toLowerCase().includes(q) ||
          t.category.toLowerCase().includes(q) ||
          t.tags.some((tag) => tag.toLowerCase().includes(q))
        );
      });
  }, [state, search, account, category]);

  async function onCategoryChange(id: string, next: string) {
    try {
      await patchTransaction(id, { category: next });
      await onRefresh();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Category save failed", true);
    }
  }

  async function removeTag(tx: Transaction, tag: string) {
    try {
      const tags = tx.tags.filter((t) => t !== tag);
      await patchTransaction(tx.id, { tags });
      await onRefresh();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Tag remove failed", true);
    }
  }

  function openTagModal(tx: Transaction) {
    setTagTx(tx);
    setSelectedTags(tx.tags);
    setNewTag("");
  }

  async function saveTags() {
    if (!tagTx) return;
    setSaving(true);
    try {
      let tags = [...selectedTags];
      if (newTag.trim()) {
        const n = newTag.trim();
        if (!tags.some((t) => t.toLowerCase() === n.toLowerCase())) tags.push(n);
      }
      await patchTransaction(tagTx.id, { tags });
      if (newTag.trim()) {
        await fetch("/api/tags", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: newTag.trim() }),
        });
      }
      setTagTx(null);
      await onRefresh();
      toast("Tags updated");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Tag save failed", true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack">
      <div className="filters">
        <div className="field" style={{ flex: 1, minWidth: 180 }}>
          <label htmlFor="search">Search</label>
          <input
            id="search"
            className="control"
            placeholder="Merchant, category, or tag"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="field" style={{ minWidth: 160 }}>
          <label htmlFor="account">Account</label>
          <select id="account" className="control" value={account} onChange={(e) => setAccount(e.target.value)}>
            <option value="all">All accounts</option>
            {state.settings.accounts.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>
        <div className="field" style={{ minWidth: 160 }}>
          <label htmlFor="category">Category</label>
          <select id="category" className="control" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="all">All categories</option>
            {state.settings.categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="field" style={{ minWidth: 160 }}>
          <label htmlFor="tx-period">Date period</label>
          <select
            id="tx-period"
            className="control"
            value={state.settings.selectedPeriod}
            disabled={savingPeriod}
            onChange={(e) => onPeriodChange(e.target.value as PeriodKey)}
          >
            {PERIOD_OPTIONS.map((o) => (
              <option key={o.key} value={o.key}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="card empty-state">No transactions match these filters.</div>
      ) : (
        <div className="table-wrap card" style={{ padding: 0 }}>
          <table className="data">
            <thead>
              <tr>
                <th>Date / Merchant</th>
                <th>Category</th>
                <th>Account</th>
                <th>Tags</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id}>
                  <td>
                    <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                      {t.merchant}
                      {t.receipt ? <Receipt size={14} aria-label="Receipt matched" /> : null}
                    </div>
                    <div className="helper">{t.date}</div>
                  </td>
                  <td>
                    <select
                      className="control"
                      aria-label={`Category for ${t.merchant}`}
                      value={t.category}
                      onChange={(e) => onCategoryChange(t.id, e.target.value)}
                      style={{ minWidth: 140 }}
                    >
                      {state.settings.categories.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                      {!state.settings.categories.includes(t.category) ? (
                        <option value={t.category}>{t.category}</option>
                      ) : null}
                    </select>
                  </td>
                  <td>{t.account}</td>
                  <td>
                    <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center" }}>
                      {t.tags.map((tag) => (
                        <span className="pill" key={tag}>
                          {tag}
                          <button type="button" aria-label={`Remove ${tag}`} onClick={() => removeTag(t, tag)}>
                            ×
                          </button>
                        </span>
                      ))}
                      <button
                        type="button"
                        className="btn btn-ghost"
                        style={{ minHeight: 32, padding: "0 8px" }}
                        aria-label="Add tags"
                        onClick={() => openTagModal(t)}
                      >
                        <Plus size={16} />
                      </button>
                    </div>
                  </td>
                  <td className={t.type === "income" ? "amount-income" : "amount-expense"}>
                    {t.type === "income" ? "+" : "-"}
                    {formatMoney(t.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal title="Edit tags" open={!!tagTx} onClose={() => setTagTx(null)}>
        <p className="helper" style={{ marginTop: 0 }}>
          Select existing tags or type a new tag name. No category is required.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
          {state.tags.map((t) => {
            const on = selectedTags.some((s) => s.toLowerCase() === t.name.toLowerCase());
            return (
              <button
                key={t.name}
                type="button"
                className="btn"
                style={{
                  minHeight: 36,
                  background: on ? "var(--violet-soft)" : undefined,
                  borderColor: on ? "var(--violet)" : undefined,
                }}
                onClick={() => {
                  setSelectedTags((prev) =>
                    on
                      ? prev.filter((x) => x.toLowerCase() !== t.name.toLowerCase())
                      : [...prev, t.name]
                  );
                }}
              >
                {t.name}
              </button>
            );
          })}
        </div>
        <div className="field">
          <label htmlFor="new-tag">New tag</label>
          <input
            id="new-tag"
            className="control"
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            placeholder="Tag name only"
          />
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={() => setTagTx(null)}>Cancel</button>
          <button type="button" className="btn btn-primary" disabled={saving} onClick={saveTags}>
            {saving ? "Saving…" : "Save tags"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
