import { useEffect, useState } from "react";
import { ContextBuilder } from "../components/compose/ContextBuilder";
import { SuggestionsPanel } from "../components/compose/SuggestionsPanel";
import { useWorkspace } from "../hooks/useWorkspace";
import { api } from "../services/api";
import type { EmailGenerateResponse, PromptTemplate, Settings } from "../types";

export function ComposePage() {
  const { current } = useWorkspace();
  const [notes, setNotes] = useState("");
  const [subject, setSubject] = useState("");
  const [extra, setExtra] = useState("");
  const [sources, setSources] = useState<string[]>([
    "architecture",
    "chatgpt_knowledge",
    "project_documents",
  ]);
  const [useStyle, setUseStyle] = useState(true);
  const [useKb, setUseKb] = useState(true);
  const [promptId, setPromptId] = useState<number | "">("");
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [result, setResult] = useState<EmailGenerateResponse | null>(null);
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.prompts.list().then(setPrompts).catch(console.error);
    api.settings.get().then(setSettings).catch(console.error);
  }, []);

  const generate = async () => {
    if (!notes.trim()) return;
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await api.emails.compose({
        rough_notes: notes,
        subject: subject || undefined,
        workspace_id: current?.id,
        context_sources: sources,
        use_style_memory: useStyle,
        use_knowledge_base: useKb,
        extra_instructions: extra || undefined,
        prompt_template_id: promptId || undefined,
      });
      setResult(res);
      setOutput(res.generated_text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate");
    } finally {
      setLoading(false);
    }
  };

  const rewrite = async (mode: string) => {
    if (!output.trim()) return;
    setRewriting(true);
    setError("");
    try {
      const res = await api.emails.rewrite({
        text: output,
        mode,
        workspace_id: current?.id,
      });
      setOutput(res.generated_text);
      setResult((prev) =>
        prev
          ? { ...prev, id: res.id, generated_text: res.generated_text, suggestions: null }
          : res
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rewrite failed");
    } finally {
      setRewriting(false);
    }
  };

  const saveFinal = async () => {
    if (!result) return;
    try {
      await api.emails.saveFinal(result.id, output, true);
      setMessage("Saved as final email and added to style memory.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const modes = settings?.available_rewrite_modes || {};

  return (
    <div>
      <h1 className="page-title">Compose Email</h1>
      <p className="page-desc">
        Paste rough thoughts — get a client-ready CTO-level email grounded in your knowledge base.
      </p>

      {error && <div className="error-banner">{error}</div>}
      {message && <div className="success-banner">{message}</div>}

      <div className="grid-2">
        <div>
          <div className="panel">
            <h3 className="panel-title">Input</h3>
            <div style={{ marginBottom: "0.85rem" }}>
              <label className="field-label">Subject (optional)</label>
              <input
                className="input"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. Horizontal Scaling Support"
              />
            </div>
            <div style={{ marginBottom: "0.85rem" }}>
              <label className="field-label">Prompt template</label>
              <select
                className="select"
                value={promptId}
                onChange={(e) =>
                  setPromptId(e.target.value ? Number(e.target.value) : "")
                }
              >
                <option value="">None (freeform compose)</option>
                {prompts.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <label className="field-label">Rough notes</label>
            <textarea
              className="textarea tall"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Client is asking whether we support horizontal scaling. We actually support it but only with Kubernetes deployment. Mention HA architecture and failover."
            />
            <div style={{ marginTop: "0.85rem" }}>
              <label className="field-label">Extra instructions</label>
              <textarea
                className="textarea"
                style={{ minHeight: 80 }}
                value={extra}
                onChange={(e) => setExtra(e.target.value)}
                placeholder="Keep under 200 words, mention Q3 timeline…"
              />
            </div>
            <div style={{ marginTop: "1rem" }}>
              <ContextBuilder selected={sources} onChange={setSources} />
            </div>
            <div className="btn-row" style={{ marginTop: "1rem" }}>
              <label className="chip">
                <input
                  type="checkbox"
                  checked={useStyle}
                  onChange={(e) => setUseStyle(e.target.checked)}
                />{" "}
                Style memory
              </label>
              <label className="chip">
                <input
                  type="checkbox"
                  checked={useKb}
                  onChange={(e) => setUseKb(e.target.checked)}
                />{" "}
                Knowledge base
              </label>
            </div>
            <div className="btn-row" style={{ marginTop: "1rem" }}>
              <button className="btn btn-primary" onClick={generate} disabled={loading}>
                {loading && <span className="spinner" />}
                Generate Email
              </button>
            </div>
          </div>
        </div>

        <div>
          <div className="panel">
            <h3 className="panel-title">Generated Email</h3>
            {result && (
              <div className="btn-row" style={{ marginBottom: "0.75rem" }}>
                <span className="badge ok">
                  {result.provider} · {result.model}
                </span>
              </div>
            )}
            <textarea
              className="textarea output"
              value={output}
              onChange={(e) => setOutput(e.target.value)}
              placeholder="Generated email will appear here…"
            />
            <div className="btn-row" style={{ marginTop: "0.85rem" }}>
              <button
                className="btn btn-primary"
                onClick={saveFinal}
                disabled={!result || !output}
              >
                Save Final + Style
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => navigator.clipboard.writeText(output)}
                disabled={!output}
              >
                Copy
              </button>
            </div>
          </div>

          <div className="panel">
            <h3 className="panel-title">Rewrite Modes</h3>
            <div className="chip-group">
              {Object.entries(modes).map(([key, desc]) => (
                <button
                  key={key}
                  type="button"
                  className="chip mode"
                  title={desc}
                  disabled={!output || rewriting}
                  onClick={() => rewrite(key)}
                >
                  {key.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          </div>

          <SuggestionsPanel suggestions={result?.suggestions} />
        </div>
      </div>
    </div>
  );
}
