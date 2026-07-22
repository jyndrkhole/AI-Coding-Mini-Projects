import { useEffect, useState } from "react";
import { useWorkspace } from "../hooks/useWorkspace";
import { api } from "../services/api";
import type { Document } from "../types";

const CATEGORIES = [
  "general",
  "architecture",
  "design",
  "requirements",
  "meeting_notes",
  "notes",
  "proposal",
  "sop",
  "email",
  "chatgpt_history",
];

export function KnowledgePage() {
  const { current } = useWorkspace();
  const [docs, setDocs] = useState<Document[]>([]);
  const [category, setCategory] = useState("general");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [chatgptTitle, setChatgptTitle] = useState("ChatGPT Conversation");
  const [chatgptContent, setChatgptContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = async () => {
    if (!current) return;
    const list = await api.knowledge.list(current.id);
    setDocs(list);
  };

  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, [current?.id]);

  const onUpload = async (file: File | null) => {
    if (!file || !current) return;
    setLoading(true);
    setError("");
    try {
      await api.knowledge.upload(current.id, file, category);
      setMessage(`Uploaded ${file.name}`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  const ingestText = async () => {
    if (!current || !title.trim() || !text.trim()) return;
    setLoading(true);
    setError("");
    try {
      await api.knowledge.ingestText({
        workspace_id: current.id,
        title,
        content: text,
        category,
      });
      setMessage("Text ingested into knowledge base");
      setTitle("");
      setText("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ingest failed");
    } finally {
      setLoading(false);
    }
  };

  const importChatGPT = async () => {
    if (!current || !chatgptContent.trim()) return;
    setLoading(true);
    setError("");
    try {
      await api.knowledge.importChatGPT({
        workspace_id: current.id,
        title: chatgptTitle,
        content: chatgptContent,
      });
      setMessage("ChatGPT conversation imported into RAG");
      setChatgptContent("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setLoading(false);
    }
  };

  const remove = async (id: number) => {
    await api.knowledge.delete(id);
    await refresh();
  };

  return (
    <div>
      <h1 className="page-title">Knowledge Base</h1>
      <p className="page-desc">
        Upload PDFs, DOCX, images, Markdown, notes, and your ChatGPT history. Everything is
        chunked, embedded, and searchable per workspace.
      </p>

      {error && <div className="error-banner">{error}</div>}
      {message && <div className="success-banner">{message}</div>}

      <div className="grid-2">
        <div>
          <div className="panel">
            <h3 className="panel-title">Upload Document</h3>
            <label className="field-label">Category</label>
            <select
              className="select"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <div style={{ marginTop: "0.85rem" }}>
              <input
                type="file"
                accept=".pdf,.docx,.txt,.md,.markdown,.json,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
                onChange={(e) => onUpload(e.target.files?.[0] || null)}
                disabled={loading || !current}
              />
            </div>
            <p style={{ fontSize: "0.8rem", color: "var(--text-dim)", marginTop: "0.75rem" }}>
              Supported: PDF, DOCX, TXT, Markdown, JSON, PNG, JPG, WEBP, BMP, TIFF
            </p>
          </div>

          <div className="panel">
            <h3 className="panel-title">Paste Text / Notes</h3>
            <input
              className="input"
              placeholder="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              style={{ marginBottom: "0.65rem" }}
            />
            <textarea
              className="textarea"
              placeholder="Paste meeting notes, SOPs, architecture notes…"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <button
              className="btn btn-primary"
              style={{ marginTop: "0.75rem" }}
              onClick={ingestText}
              disabled={loading}
            >
              Ingest Text
            </button>
          </div>
        </div>

        <div>
          <div className="panel">
            <h3 className="panel-title">Import ChatGPT History</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: 0 }}>
              Export your conversation as JSON or paste plain text / markdown. Direct shared-link
              import is not supported due to platform restrictions.
            </p>
            <input
              className="input"
              value={chatgptTitle}
              onChange={(e) => setChatgptTitle(e.target.value)}
              style={{ marginBottom: "0.65rem" }}
            />
            <textarea
              className="textarea tall"
              placeholder="Paste ChatGPT export JSON or conversation text…"
              value={chatgptContent}
              onChange={(e) => setChatgptContent(e.target.value)}
            />
            <button
              className="btn btn-primary"
              style={{ marginTop: "0.75rem" }}
              onClick={importChatGPT}
              disabled={loading}
            >
              {loading && <span className="spinner" />}
              Import Conversation
            </button>
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: "1rem" }}>
        <h3 className="panel-title">Documents in Workspace</h3>
        {docs.length === 0 ? (
          <div className="empty">No documents yet.</div>
        ) : (
          <div className="list">
            {docs.map((d) => (
              <div
                key={d.id}
                className="list-item"
                style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}
              >
                <div>
                  <h4>{d.original_name}</h4>
                  <p>
                    {d.file_type} · {d.category} · {d.chunk_count} chunks ·{" "}
                    <span className={`badge ${d.status === "ready" ? "ok" : "warn"}`}>
                      {d.status}
                    </span>
                  </p>
                </div>
                <button className="btn btn-danger" onClick={() => remove(d.id)}>
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
