import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { Settings } from "../types";

export function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [form, setForm] = useState<Record<string, string | number>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.settings
      .get()
      .then((s) => {
        setSettings(s);
        setForm({
          llm_provider: s.llm_provider,
          llm_model: s.llm_model,
          llm_temperature: s.llm_temperature,
          llm_max_tokens: s.llm_max_tokens,
          ollama_base_url: s.ollama_base_url,
          ollama_model: s.ollama_model,
          embedding_provider: s.embedding_provider,
          embedding_model: s.embedding_model,
          chunk_size: s.chunk_size,
          chunk_overlap: s.chunk_overlap,
          retrieval_top_k: s.retrieval_top_k,
          groq_api_key: "",
        });
      })
      .catch((e) => setError(e.message));
  }, []);

  const save = async () => {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const payload: Record<string, unknown> = { ...form };
      if (!payload.groq_api_key) delete payload.groq_api_key;
      const updated = await api.settings.update(payload);
      setSettings(updated);
      setMessage("Settings saved. Provider can be switched without code changes.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (!settings) return <div className="empty">Loading settings…</div>;

  return (
    <div>
      <h1 className="page-title">AI Settings</h1>
      <p className="page-desc">
        Configure LLM providers, embeddings, and RAG parameters. Switch between Groq and Ollama
        from the UI.
      </p>
      {error && <div className="error-banner">{error}</div>}
      {message && <div className="success-banner">{message}</div>}

      <div className="panel" style={{ marginBottom: "1rem" }}>
        <div className="btn-row">
          <span className={`badge ${settings.provider_healthy ? "ok" : "warn"}`}>
            {settings.provider_healthy ? "Provider healthy" : "Provider unreachable"}
          </span>
          <span className="badge">
            Active: {settings.llm_provider} / {settings.llm_model}
          </span>
          <span className="badge">
            Groq key: {settings.groq_api_key_set ? "configured" : "missing"}
          </span>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3 className="panel-title">LLM Provider</h3>
          <Field label="Provider">
            <select
              className="select"
              value={String(form.llm_provider)}
              onChange={(e) => setForm({ ...form, llm_provider: e.target.value })}
            >
              <option value="groq">Groq</option>
              <option value="ollama">Ollama (local)</option>
            </select>
          </Field>
          <Field label="Model">
            <input
              className="input"
              value={String(form.llm_model)}
              onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
              placeholder="llama-3.3-70b-versatile or llama3"
            />
          </Field>
          <Field label="Temperature">
            <input
              className="input"
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={Number(form.llm_temperature)}
              onChange={(e) => setForm({ ...form, llm_temperature: Number(e.target.value) })}
            />
          </Field>
          <Field label="Max tokens">
            <input
              className="input"
              type="number"
              value={Number(form.llm_max_tokens)}
              onChange={(e) => setForm({ ...form, llm_max_tokens: Number(e.target.value) })}
            />
          </Field>
          <Field label="Groq API key (leave blank to keep current)">
            <input
              className="input"
              type="password"
              value={String(form.groq_api_key || "")}
              onChange={(e) => setForm({ ...form, groq_api_key: e.target.value })}
              placeholder="gsk_…"
            />
          </Field>
          <Field label="Ollama base URL">
            <input
              className="input"
              value={String(form.ollama_base_url)}
              onChange={(e) => setForm({ ...form, ollama_base_url: e.target.value })}
            />
          </Field>
          <Field label="Ollama model">
            <input
              className="input"
              value={String(form.ollama_model)}
              onChange={(e) => setForm({ ...form, ollama_model: e.target.value })}
            />
          </Field>
        </div>

        <div className="panel">
          <h3 className="panel-title">RAG / Embeddings</h3>
          <Field label="Embedding provider">
            <select
              className="select"
              value={String(form.embedding_provider)}
              onChange={(e) => setForm({ ...form, embedding_provider: e.target.value })}
            >
              <option value="local">Local (sentence-transformers)</option>
              <option value="ollama">Ollama</option>
            </select>
          </Field>
          <Field label="Embedding model">
            <input
              className="input"
              value={String(form.embedding_model)}
              onChange={(e) => setForm({ ...form, embedding_model: e.target.value })}
            />
          </Field>
          <Field label="Chunk size">
            <input
              className="input"
              type="number"
              value={Number(form.chunk_size)}
              onChange={(e) => setForm({ ...form, chunk_size: Number(e.target.value) })}
            />
          </Field>
          <Field label="Chunk overlap">
            <input
              className="input"
              type="number"
              value={Number(form.chunk_overlap)}
              onChange={(e) => setForm({ ...form, chunk_overlap: Number(e.target.value) })}
            />
          </Field>
          <Field label="Retrieval top-K">
            <input
              className="input"
              type="number"
              value={Number(form.retrieval_top_k)}
              onChange={(e) => setForm({ ...form, retrieval_top_k: Number(e.target.value) })}
            />
          </Field>
        </div>
      </div>

      <button
        className="btn btn-primary"
        style={{ marginTop: "1rem" }}
        onClick={save}
        disabled={saving}
      >
        {saving && <span className="spinner" />}
        Save Settings
      </button>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "0.85rem" }}>
      <label className="field-label">{label}</label>
      {children}
    </div>
  );
}
