import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalyzeBody, Report } from "../types";

const PERCENT_KEYS = [
  "revenue_growth",
  "operating_margin",
  "tax_rate",
  "capex_pct_revenue",
  "nwc_pct_revenue",
  "discount_rate",
  "terminal_growth",
];

export function ReportView({
  report,
  busy,
  onRerun,
}: {
  report: Report;
  busy: boolean;
  onRerun: (assumptions: AnalyzeBody["assumptions"]) => void;
}) {
  const currency = report.currency;
  const price = report.market.price;
  const [draft, setDraft] = useState<Record<string, string>>({});

  useEffect(() => {
    const next: Record<string, string> = {};
    for (const item of report.assumptions) {
      const value = Array.isArray(item.value) ? item.value[0] : item.value;
      if (typeof value !== "number") continue;
      next[item.key] = PERCENT_KEYS.includes(item.key) ? (value * 100).toFixed(2) : String(value);
    }
    setDraft(next);
  }, [report.id, report.assumptions]);

  const sensitivity = useMemo(() => grid(report.valuation.dcf.sensitivity), [report]);
  const traceEnd = Math.max(...report.trace.map((span) => span.started_offset_ms + span.duration_ms), 1);

  function rerun(event: FormEvent) {
    event.preventDefault();
    const assumptions: NonNullable<AnalyzeBody["assumptions"]> = { forecast_years: 5 };
    for (const item of report.assumptions) {
      if (!PERCENT_KEYS.includes(item.key)) continue;
      const original = Array.isArray(item.value) ? item.value[0] : item.value;
      const edited = Number(draft[item.key]);
      if (typeof original !== "number" || Number.isNaN(edited)) continue;
      if (Math.abs(edited / 100 - original) > 0.000001) {
        const key = item.key as keyof NonNullable<AnalyzeBody["assumptions"]>;
        assumptions[key] = edited / 100;
      }
    }
    onRerun(assumptions);
  }

  return (
    <div className="report">
      <article>
        <header className="verdict">
          <p className="kicker">
            {report.company_name} · {report.ticker}
            {report.market.exchange ? ` · ${report.market.exchange}` : ""}
          </p>
          <div className="verdict-row">
            <h2 className={`rating ${tone(report.rating.label)}`}>{label(report.rating.label)}</h2>
            <dl>
              <div>
                <dt>Price</dt>
                <dd>{perShare(price, currency)}</dd>
              </div>
              <div>
                <dt>Value used</dt>
                <dd>{perShare(report.valuation.intrinsic_value_per_share, currency)}</dd>
              </div>
              <div>
                <dt>Upside</dt>
                <dd>{points(report.valuation.upside_percent)}</dd>
              </div>
              <div>
                <dt>Confidence</dt>
                <dd>{report.rating.confidence}</dd>
              </div>
            </dl>
          </div>
          <div className="chips">
            <Chip name="Health" value={report.disagreement.financial_health} />
            <Chip name="Valuation" value={report.disagreement.valuation} />
            <Chip name="Risk" value={report.disagreement.risk} />
            <Chip name="News" value={report.disagreement.news} />
          </div>
          {report.rating.score != null && (
            <p className="score">
              Rating score {report.rating.score.toFixed(2)} / 5.{" "}
              {report.rating.components.map((item) => `${item.name} ${Math.round(item.weight * 100)}%`).join(" · ")}
            </p>
          )}
        </header>

        <section className={report.disagreement.consistent ? "note" : "note conflict"}>
          <h3>{report.disagreement.consistent ? "Specialist labels" : "Where the agents disagree"}</h3>
          {report.disagreement.consistent ? (
            <p>The configured conflict rules did not fire. The four labels above are still independent results.</p>
          ) : (
            <ul>
              {report.disagreement.conflicts.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </section>

        {report.health.history.length > 1 && (
          <section className="chart-block">
            <h3>Revenue and margins</h3>
            <p className="caption">Annual reported figures. Margins are calculated, not forecast.</p>
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={report.health.history}>
                <CartesianGrid stroke="var(--line)" vertical={false} />
                <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                <YAxis yAxisId="left" tickFormatter={(value) => compactAxis(Number(value))} width={56} />
                <YAxis yAxisId="right" orientation="right" tickFormatter={(value) => `${(Number(value) * 100).toFixed(0)}%`} width={42} />
                <Tooltip formatter={(value, name) => formatTooltip(value, String(name))} />
                <Legend />
                <Bar yAxisId="left" dataKey="revenue" name="Revenue" fill="var(--ink)" radius={[3, 3, 0, 0]} />
                <Line yAxisId="right" dataKey="operating_margin" name="Operating margin" stroke="var(--good)" strokeWidth={2} dot={false} />
                <Line yAxisId="right" dataKey="net_margin" name="Net margin" stroke="var(--warn)" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </section>
        )}

        <form className="assumptions" onSubmit={rerun}>
          <div>
            <h3>Forecast assumptions</h3>
            <p>Change a rate and rerun. Blank fields keep the derived value. Percent fields are entered as percentages.</p>
          </div>
          <div className="assumption-grid">
            {report.assumptions
              .filter((item) => PERCENT_KEYS.includes(item.key) && draft[item.key] !== undefined)
              .map((item) => (
                <label key={item.key}>
                  <span>{item.label}</span>
                  <input
                    inputMode="decimal"
                    value={draft[item.key] ?? ""}
                    onChange={(event) => setDraft({ ...draft, [item.key]: event.target.value })}
                  />
                  <small>{item.source.replaceAll("_", " ")}</small>
                </label>
              ))}
          </div>
          <button type="submit" disabled={busy}>
            {busy ? "Rerunning" : "Rerun valuation"}
          </button>
        </form>

        {sensitivity.rates.length > 0 && (
          <section>
            <h3>DCF sensitivity</h3>
            <p className="caption">Value per share. Invalid pairs, where terminal growth is not below the discount rate, are omitted.</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Discount \ growth</th>
                    {sensitivity.growths.map((growth) => (
                      <th key={growth}>{(growth * 100).toFixed(1)}%</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sensitivity.rates.map((rate) => (
                    <tr key={rate}>
                      <th>{(rate * 100).toFixed(1)}%</th>
                      {sensitivity.growths.map((growth) => {
                        const value = sensitivity.lookup.get(`${rate}|${growth}`);
                        return (
                          <td key={growth} style={{ background: value == null ? undefined : shade(value, price) }}>
                            {value == null ? "—" : value.toFixed(1)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {report.sections.map((section) => (
          <section key={section.id} id={section.id}>
            <h3>{section.title}</h3>
            {section.paragraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
            {section.bullets.length > 0 && (
              <ul>
                {section.bullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
            )}
            {section.interpretation && (
              <p className="interpretation">Model commentary: {section.interpretation}</p>
            )}
          </section>
        ))}
        <p className="disclaimer">{report.disclaimer}</p>
      </article>

      <aside className="rail">
        <section>
          <h3>Market</h3>
          <dl className="facts">
            <div>
              <dt>Market cap</dt>
              <dd>{money(report.market.market_cap, currency)}</dd>
            </div>
            <div>
              <dt>Enterprise value</dt>
              <dd>{money(report.market.enterprise_value, currency)}</dd>
            </div>
            <div>
              <dt>Beta</dt>
              <dd>{report.market.beta?.toFixed(2) ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Industry</dt>
              <dd>{report.market.industry ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>DCF</dt>
              <dd>
                {report.valuation.dcf.status} · {report.valuation.dcf.model.replaceAll("_", " ")}
              </dd>
            </div>
            <div>
              <dt>Data</dt>
              <dd>
                {report.data_quality.confidence} · {report.data_quality.years_annual} annual years
              </dd>
            </div>
          </dl>
        </section>

        {report.valuation.peers.length > 0 && (
          <section>
            <h3>Peer multiples</h3>
            <p className="caption">{report.valuation.peer_selection}</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>P/E</th>
                    <th>P/S</th>
                    <th>EV/EBITDA</th>
                  </tr>
                </thead>
                <tbody>
                  {report.valuation.target_multiples && (
                    <tr>
                      <th>{report.valuation.target_multiples.ticker}</th>
                      <td>{multiple(report.valuation.target_multiples.price_to_earnings)}</td>
                      <td>{multiple(report.valuation.target_multiples.price_to_sales)}</td>
                      <td>{multiple(report.valuation.target_multiples.ev_to_ebitda)}</td>
                    </tr>
                  )}
                  {report.valuation.peers.map((peer) => (
                    <tr key={peer.ticker}>
                      <th>{peer.ticker}</th>
                      <td>{peer.excluded_reason ? "—" : multiple(peer.price_to_earnings)}</td>
                      <td>{peer.excluded_reason ? "—" : multiple(peer.price_to_sales)}</td>
                      <td>{peer.excluded_reason ? "—" : multiple(peer.ev_to_ebitda)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <section>
          <h3>Scenarios</h3>
          <ul className="scenarios">
            {report.valuation.scenarios.map((scenario) => (
              <li key={scenario.name}>
                <strong>{scenario.name}</strong>
                <span>{perShare(scenario.intrinsic_value_per_share, currency)}</span>
                <span>{points(scenario.upside_percent)}</span>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h3>Risk flags</h3>
          <ul className="flags">
            {report.risk.flags.length === 0 && <li>No flag was raised from the signals that could be evaluated.</li>}
            {report.risk.flags.map((flag) => (
              <li key={`${flag.title}-${flag.evidence}`}>
                <span className={`sev ${flag.severity}`}>{flag.severity}</span>
                <strong>{flag.title}</strong>
                <p>{flag.evidence}</p>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h3>News · {label(report.news.label)}</h3>
          <ul className="news">
            {report.news.articles.length === 0 && <li>No headlines were returned for this lookback.</li>}
            {report.news.articles.slice(0, 6).map((article) => (
              <li key={article.url ?? article.title}>
                {article.url ? (
                  <a href={article.url} target="_blank" rel="noreferrer">
                    {article.title}
                  </a>
                ) : (
                  article.title
                )}
                <small>
                  {article.publisher ?? "Unknown publisher"} · {label(article.sentiment)}
                </small>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h3>Agent timing</h3>
          <p className="caption">Offset from the start of this run. Overlapping bars ran together.</p>
          <ul className="trace">
            {report.trace.map((span) => (
              <li key={`${span.name}-${span.started_offset_ms}`}>
                <span>{span.name}</span>
                <div className="track">
                  <i
                    style={{
                      marginLeft: `${(span.started_offset_ms / traceEnd) * 100}%`,
                      width: `${Math.max((span.duration_ms / traceEnd) * 100, 1.5)}%`,
                    }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </section>
      </aside>
    </div>
  );
}

function Chip({ name, value }: { name: string; value: string }) {
  return (
    <span className={`chip ${tone(value)}`}>
      <small>{name}</small>
      {label(value)}
    </span>
  );
}

function grid(cells: Report["valuation"]["dcf"]["sensitivity"]) {
  const rates = [...new Set(cells.map((cell) => cell.discount_rate))].sort((a, b) => a - b);
  const growths = [...new Set(cells.map((cell) => cell.terminal_growth))].sort((a, b) => a - b);
  const lookup = new Map(cells.map((cell) => [`${cell.discount_rate}|${cell.terminal_growth}`, cell.value_per_share]));
  return { rates, growths, lookup };
}

function label(value: string) {
  return value.replaceAll("_", " ");
}

function tone(value: string) {
  if (value.includes("INSUFFICIENT")) return "muted";
  if (["SELL", "WEAK", "HIGH", "OVERVALUED", "BEARISH"].some((part) => value.includes(part))) return "bad";
  if (["STRONG_BUY", "BUY", "STRONG", "SOLID", "UNDERVALUED", "BULLISH", "LOW"].some((part) => value.includes(part))) return "good";
  return "warn";
}

function money(value: number | null, currency: string | null) {
  if (value == null) return "Unavailable";
  const sign = value < 0 ? "-" : "";
  const amount = Math.abs(value);
  const prefix = symbol(currency);
  for (const [unit, scale] of [
    ["T", 1e12],
    ["B", 1e9],
    ["M", 1e6],
  ] as const) {
    if (amount >= scale) return `${sign}${prefix}${(amount / scale).toFixed(2)}${unit}`;
  }
  return `${sign}${prefix}${amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function perShare(value: number | null, currency: string | null) {
  if (value == null) return "Unavailable";
  return `${symbol(currency)}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function symbol(currency: string | null) {
  if (currency === "USD") return "$";
  if (currency === "INR") return "₹";
  if (currency === "EUR") return "€";
  if (currency === "GBP") return "£";
  return currency ? `${currency} ` : "";
}

function points(value: number | null) {
  if (value == null) return "Unavailable";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function multiple(value: number | null) {
  return value == null ? "—" : value.toFixed(1);
}

function compactAxis(value: number) {
  const amount = Math.abs(value);
  if (amount >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (amount >= 1e9) return `${(value / 1e9).toFixed(0)}B`;
  if (amount >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
  return String(value);
}

function formatTooltip(value: unknown, name: string) {
  const number = typeof value === "number" ? value : Number(value);
  if (name.toLowerCase().includes("margin")) return [`${(number * 100).toFixed(1)}%`, name];
  return [compactAxis(number), name];
}

function shade(value: number, price: number | null) {
  if (!price) return "transparent";
  const gap = (value - price) / price;
  const alpha = Math.min(0.4, Math.abs(gap)).toFixed(2);
  return gap >= 0 ? `rgba(29, 107, 74, ${alpha})` : `rgba(141, 47, 47, ${alpha})`;
}
