import { useEffect, useState } from "react";
import { analyze, getHistory, getReport, getStatus } from "./api";
import { ReportView } from "./components/ReportView";
import type { AnalyzeBody, HistoryItem, Report, Status } from "./types";

export function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [peers, setPeers] = useState("");
  const [lookback, setLookback] = useState(30);
  const [report, setReport] = useState<Report | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [status, setStatus] = useState<Status | null>(null);
  const [phase, setPhase] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getStatus().then(setStatus).catch(() => undefined);
    getHistory().then(setHistory).catch(() => undefined);
  }, []);

  async function run(assumptions?: AnalyzeBody["assumptions"]) {
    const symbol = ticker.trim();
    if (!symbol) return;
    setBusy(true);
    setError("");
    setPhase("Fetching price, statements, and headlines");
    const peerList = peers
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    try {
      const next = await analyze(
        {
          ticker: symbol,
          news_lookback_days: lookback,
          peers: peerList.length ? peerList : undefined,
          assumptions,
        },
        (event) => {
          if (event.type === "phase") setPhase(phaseText(event.phase));
        },
      );
      setReport(next);
      setHistory(await getHistory());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed.");
    } finally {
      setBusy(false);
      setPhase("");
    }
  }

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <img src="/favicon.svg" alt="" width="36" height="36" />
          <div>
            <span>Research desk</span>
            <strong>Fundamental Analyser</strong>
          </div>
        </div>
        <form
          className="ticket"
          onSubmit={(event) => {
            event.preventDefault();
            void run();
          }}
        >
          <label>
            Ticker
            <input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} placeholder="AAPL or TCS.NS" />
          </label>
          <label>
            Peers
            <input value={peers} onChange={(event) => setPeers(event.target.value.toUpperCase())} placeholder="Optional, comma separated" />
          </label>
          <label>
            News days
            <input
              type="number"
              min={1}
              max={365}
              value={lookback}
              onChange={(event) => setLookback(Number(event.target.value))}
            />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? "Analysing" : "Analyse"}
          </button>
        </form>
        <p className="llm">
          {status == null
            ? "Checking model configuration"
            : status.llm_configured
              ? `Commentary: ${status.llm_provider} · ${status.llm_model}`
              : status.llm_message || "Commentary is rule-based until an LLM provider is configured."}
        </p>
      </header>

      <div className="shell">
        <aside className="history">
          <h2>Saved runs</h2>
          {history.length === 0 && <p>Completed analyses are stored locally in SQLite.</p>}
          <ul>
            {history.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => {
                    getReport(item.id).then(setReport).catch((caught: unknown) => {
                      setError(caught instanceof Error ? caught.message : "Could not open that report.");
                    });
                  }}
                >
                  <strong>{item.ticker}</strong>
                  <span>{item.rating.replaceAll("_", " ")}</span>
                  <small>{new Date(item.created_at).toLocaleString()}</small>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <main>
          {error && <p className="error">{error}</p>}
          {busy && <p className="phase">{phase}</p>}
          {!report && !busy && (
            <section className="intro">
              <h2>What is the financial health, value, and risk of this stock?</h2>
              <p>
                Enter a ticker. Three specialists read the same cached statements at once: financial health, news, and risk.
                Valuation starts once the statements are in, without waiting for headlines. The brief is written last, and it
                keeps those conclusions even when they conflict.
              </p>
              <ol>
                <li>Reported figures stay reported. Missing fields stay missing.</li>
                <li>Ratios, the discounted cash flow, peer multiples, risk, and the rating are calculated in code.</li>
                <li>A language model, when configured, may comment. It does not choose the rating.</li>
              </ol>
            </section>
          )}
          {report && (
            <>
              <div className="toolbar">
                <button
                  type="button"
                  onClick={() => {
                    void navigator.clipboard.writeText(report.brief_markdown);
                  }}
                >
                  Copy brief
                </button>
              </div>
              <ReportView report={report} busy={busy} onRerun={(assumptions) => void run(assumptions)} />
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function phaseText(phase?: string) {
  if (phase === "data") return "Fetching price, statements, and headlines";
  if (phase === "specialists") return "Financial, news, and risk agents are running together";
  if (phase === "valuation") return "Valuation is using the financial statements";
  if (phase === "report") return "Writing the brief";
  return "Working";
}
