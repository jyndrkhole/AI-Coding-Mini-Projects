import { useState } from "react";
import { useWorkspace } from "../hooks/useWorkspace";
import { api } from "../services/api";
import type { SearchResult } from "../types";

export function SearchPage() {
  const { current } = useWorkspace();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const search = async () => {
    if (!query.trim() || !current) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.knowledge.search({
        query,
        workspace_id: current.id,
        top_k: 10,
      });
      setResults(res.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="page-title">Semantic Search</h1>
      <p className="page-desc">
        Search across architecture docs, emails, meeting notes, and imported ChatGPT history.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="panel">
        <div className="chat-input-row">
          <input
            className="input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='e.g. "How did I explain Kubernetes to clients?"'
            onKeyDown={(e) => e.key === "Enter" && search()}
          />
          <button className="btn btn-primary" onClick={search} disabled={loading}>
            {loading ? <span className="spinner" /> : "Search"}
          </button>
        </div>
      </div>

      <div className="panel" style={{ marginTop: "1rem" }}>
        <h3 className="panel-title">Results ({results.length})</h3>
        {results.length === 0 ? (
          <div className="empty">No results yet.</div>
        ) : (
          <div className="list">
            {results.map((r) => (
              <div key={r.id} className="list-item">
                <div className="btn-row" style={{ marginBottom: "0.4rem" }}>
                  <span className="badge ok">score {(r.score * 100).toFixed(0)}%</span>
                  <span className="badge">
                    {String(r.metadata.filename || "unknown")}
                  </span>
                  <span className="badge">{String(r.metadata.category || "")}</span>
                </div>
                <p className="mono" style={{ margin: 0, color: "var(--text)" }}>
                  {r.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
