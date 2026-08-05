"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PERIOD_OPTIONS, type AppState, type PeriodKey } from "@/lib/types";
import { formatMoney } from "@/lib/client";
import { inDateRange, inPeriod, priorPeriodRange } from "@/lib/periods";
import { detectPatterns } from "@/lib/detection";

const PIE_COLORS = ["#6558D3", "#3B82C4", "#1F9D6A", "#E08A2C", "#C94444", "#7A6EE0", "#5C6478"];

export function DashboardPage({
  state,
  onPeriodChange,
  onNavigate,
  savingPeriod,
}: {
  state: AppState;
  onPeriodChange: (p: PeriodKey) => void;
  onNavigate: (tab: string) => void;
  savingPeriod: boolean;
}) {
  const period = state.settings.selectedPeriod;
  const txs = state.transactions.filter((t) => inPeriod(t.date, period));
  const income = txs.filter((t) => t.type === "income").reduce((s, t) => s + t.amount, 0);
  const spending = txs.filter((t) => t.type === "expense").reduce((s, t) => s + t.amount, 0);
  const savingsRate = income === 0 ? 0 : ((income - spending) / income) * 100;
  const needsReview = state.transactions.filter((t) => t.category === "Needs review").length;

  const prior = priorPeriodRange(period);
  let trendIncome: string | null = null;
  let trendSpend: string | null = null;
  if (prior) {
    const priorTxs = state.transactions.filter((t) =>
      inDateRange(t.date, prior.start, prior.end)
    );
    const pIncome = priorTxs
      .filter((t) => t.type === "income")
      .reduce((s, t) => s + t.amount, 0);
    const pSpend = priorTxs
      .filter((t) => t.type === "expense")
      .reduce((s, t) => s + t.amount, 0);
    if (pIncome > 0 || income > 0) {
      const delta = income - pIncome;
      trendIncome = `${delta >= 0 ? "+" : ""}${formatMoney(delta)} vs prior period`;
    }
    if (pSpend > 0 || spending > 0) {
      const delta = spending - pSpend;
      trendSpend = `${delta >= 0 ? "+" : ""}${formatMoney(delta)} vs prior period`;
    }
  }

  // Cash flow: up to 7 monthly points
  const monthMap = new Map<string, { income: number; expense: number }>();
  for (const t of state.transactions) {
    if (!inPeriod(t.date, period) && period !== "all-time") continue;
    const key = t.date.slice(0, 7);
    const cur = monthMap.get(key) || { income: 0, expense: 0 };
    if (t.type === "income") cur.income += t.amount;
    else cur.expense += t.amount;
    monthMap.set(key, cur);
  }
  const cashFlow = [...monthMap.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-7)
    .map(([month, v]) => ({ month, ...v }));

  const catMap = new Map<string, number>();
  for (const t of txs.filter((x) => x.type === "expense")) {
    catMap.set(t.category, (catMap.get(t.category) || 0) + t.amount);
  }
  const catData = [...catMap.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
  const catTotal = catData.reduce((s, d) => s + d.value, 0);

  const recent = [...txs]
    .sort((a, b) => b.date.localeCompare(a.date) || b.createdAt.localeCompare(a.createdAt))
    .slice(0, 5);

  const suggestions = detectPatterns(
    state.transactions,
    state.settings.dismissedPatterns
  );
  const upcoming = [
    ...state.settings.recurring.filter((r) => r.active),
    ...state.settings.subscriptions.filter((s) => s.active),
  ]
    .sort((a, b) => a.nextDate.localeCompare(b.nextDate))
    .slice(0, 5);

  const netWorth = state.settings.assetsTotal - state.settings.liabilitiesTotal;

  return (
    <div className="stack">
      <div className="filters">
        <div className="field" style={{ minWidth: 180 }}>
          <label htmlFor="period">Date period</label>
          <select
            id="period"
            className="control"
            value={period}
            disabled={savingPeriod}
            onChange={(e) => onPeriodChange(e.target.value as PeriodKey)}
          >
            {PERIOD_OPTIONS.map((o) => (
              <option key={o.key} value={o.key}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="summary-grid">
        <div className="card summary-card">
          <div className="summary-label">Net Worth</div>
          <div className="summary-value">
            {state.settings.netWorthConfigured ? formatMoney(netWorth) : "Not set"}
          </div>
          <div className="summary-strip">
            {state.settings.netWorthConfigured
              ? `Assets ${formatMoney(state.settings.assetsTotal)} − Liabilities ${formatMoney(state.settings.liabilitiesTotal)}`
              : (
                <>
                  Enter assets and liabilities in{" "}
                  <button type="button" className="btn btn-ghost" style={{ minHeight: 32, padding: "0 8px" }} onClick={() => onNavigate("settings")}>
                    Settings
                  </button>
                </>
              )}
          </div>
        </div>
        <div className="card summary-card">
          <div className="summary-label">Income</div>
          <div className="summary-value" style={{ color: "var(--green)" }}>
            {formatMoney(income)}
          </div>
          <div className="summary-strip">{trendIncome || "No trend yet"}</div>
        </div>
        <div className="card summary-card">
          <div className="summary-label">Spending</div>
          <div className="summary-value" style={{ color: "var(--orange)" }}>
            {formatMoney(spending)}
          </div>
          <div className="summary-strip">{trendSpend || "No trend yet"}</div>
        </div>
        <div className="card summary-card">
          <div className="summary-label">Savings rate</div>
          <div className="summary-value">{savingsRate.toFixed(0)}%</div>
          <div className="summary-strip">
            {income === 0
              ? "No income in this period"
              : `((${formatMoney(income)} − ${formatMoney(spending)}) / ${formatMoney(income)}) × 100`}
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 className="section-title">Cash flow</h3>
          <p className="section-sub">Monthly income and expenses from saved transactions.</p>
          {cashFlow.length === 0 ? (
            <div className="empty-state">Import or add transactions to see cash flow.</div>
          ) : (
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <AreaChart data={cashFlow}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e3e6ef" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Area type="monotone" dataKey="income" stroke="#6558D3" fill="#eeebfb" name="Income" />
                  <Area type="monotone" dataKey="expense" stroke="#E08A2C" fill="#fff3e6" name="Expenses" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
        <div className="card">
          <h3 className="section-title">Spending by category</h3>
          <p className="section-sub">Expenses in the selected period.</p>
          {catData.length === 0 ? (
            <div className="empty-state">No spending in this period yet.</div>
          ) : (
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={catData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90}>
                    {catData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number, name: string) => [
                      `${formatMoney(value)} (${catTotal ? ((value / catTotal) * 100).toFixed(0) : 0}%)`,
                      name,
                    ]}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 className="section-title">Recent activity</h3>
          <p className="section-sub">Five newest transactions in this period.</p>
          {recent.length === 0 ? (
            <div className="empty-state">No transactions yet.</div>
          ) : (
            <div className="stack" style={{ gap: 10 }}>
              {recent.map((t) => (
                <div key={t.id} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{t.merchant}</div>
                    <div className="helper">
                      {t.date} · {t.category} · {t.account}
                    </div>
                  </div>
                  <div className={t.type === "income" ? "amount-income" : "amount-expense"}>
                    {t.type === "income" ? "+" : "-"}
                    {formatMoney(t.amount)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="stack">
          <div className="navy-panel">
            <h3 className="section-title" style={{ color: "white" }}>Ledgerly insight</h3>
            <p style={{ margin: 0, fontSize: 14, opacity: 0.92 }}>
              {needsReview > 0
                ? `${needsReview} transaction${needsReview === 1 ? "" : "s"} need${needsReview === 1 ? "s" : ""} review.`
                : state.transactions.length === 0
                  ? "No activity yet. Import a statement or add an entry to get started."
                  : suggestions.length > 0
                    ? `${suggestions.length} recurring pattern${suggestions.length === 1 ? "" : "s"} detected from your expenses.`
                    : "All categorized transactions look settled. No review items right now."}
            </p>
          </div>
          <div className="card">
            <h3 className="section-title">Coming up</h3>
            <p className="section-sub">Confirmed recurring payments and subscriptions.</p>
            {upcoming.length === 0 ? (
              <div className="empty-state">
                Nothing coming up.{" "}
                <button type="button" className="btn btn-ghost" onClick={() => onNavigate("recurring")}>
                  Open Recurring
                </button>
              </div>
            ) : (
              <div className="stack" style={{ gap: 10 }}>
                {upcoming.map((item) => (
                  <div key={item.id} style={{ display: "flex", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{item.name}</div>
                      <div className="helper">Due {item.nextDate}</div>
                    </div>
                    <div className="amount-expense">{formatMoney(item.amount)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
