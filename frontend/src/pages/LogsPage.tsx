import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { LogEntry } from "../types";

export function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [selected, setSelected] = useState<LogEntry | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.logs
      .list()
      .then(setLogs)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1 className="page-title">Interaction Logs</h1>
      <p className="page-desc">
        Every prompt, context block, LLM response, and final edit — for continuous improvement.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="grid-2">
        <div className="panel">
          <h3 className="panel-title">Recent Interactions</h3>
          {logs.length === 0 ? (
            <div className="empty">No logs yet.</div>
          ) : (
            <div className="list">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className="list-item"
                  style={{ cursor: "pointer" }}
                  onClick={() => setSelected(log)}
                >
                  <h4>
                    {log.action}{" "}
                    <span className="badge">
                      {log.provider}/{log.model}
                    </span>
                  </h4>
                  <p>
                    {new Date(log.created_at).toLocaleString()}
                    {log.latency_ms != null ? ` · ${log.latency_ms}ms` : ""}
                    {log.tokens_used != null ? ` · ${log.tokens_used} tokens` : ""}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="panel">
          <h3 className="panel-title">Detail</h3>
          {!selected ? (
            <div className="empty">Select a log entry.</div>
          ) : (
            <div className="list">
              <Section title="Input" text={selected.input_text} />
              <Section title="Context used" text={selected.context_used || "(none)"} />
              <Section title="Prompt" text={selected.prompt} />
              <Section title="LLM response" text={selected.llm_response} />
              {selected.final_edited && (
                <Section title="Final edited" text={selected.final_edited} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <h4 style={{ margin: "0 0 0.35rem", fontSize: "0.8rem", color: "var(--text-muted)" }}>
        {title}
      </h4>
      <pre className="log-detail mono">{text}</pre>
    </div>
  );
}
