import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { DashboardStats } from "../types";

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.dashboard()
      .then(setStats)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!stats) return <div className="empty">Loading dashboard…</div>;

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-desc">
        Your local AI email intelligence workspace — compose, retrieve context, and refine
        communications with full privacy.
      </p>

      <div className="stats-grid">
        <Stat label="Workspaces" value={stats.workspace_count} />
        <Stat label="Documents" value={stats.document_count} />
        <Stat label="Emails Generated" value={stats.email_count} />
        <Stat label="Style Examples" value={stats.style_example_count} />
        <Stat label="Prompts" value={stats.prompt_count} />
        <Stat label="Logged Interactions" value={stats.log_count} />
      </div>

      <div className="btn-row" style={{ marginBottom: "1.5rem" }}>
        <Link className="btn btn-primary" to="/compose">
          Compose Email
        </Link>
        <Link className="btn btn-secondary" to="/reply">
          Reply to Thread
        </Link>
        <Link className="btn btn-secondary" to="/knowledge">
          Import Knowledge
        </Link>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3 className="panel-title">Recent Emails</h3>
          {stats.recent_emails.length === 0 ? (
            <div className="empty">No emails yet. Start by composing one.</div>
          ) : (
            <div className="list">
              {stats.recent_emails.map((e) => (
                <div key={e.id} className="list-item">
                  <h4>
                    {e.mode} {e.subject ? `· ${e.subject}` : ""}
                  </h4>
                  <p>{e.generated_text.slice(0, 140)}…</p>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="panel">
          <h3 className="panel-title">Recent Documents</h3>
          {stats.recent_documents.length === 0 ? (
            <div className="empty">No documents imported yet.</div>
          ) : (
            <div className="list">
              {stats.recent_documents.map((d) => (
                <div key={d.id} className="list-item">
                  <h4>{d.original_name}</h4>
                  <p>
                    {d.category} · {d.chunk_count} chunks · {d.status}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
