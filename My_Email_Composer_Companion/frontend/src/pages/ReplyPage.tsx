import { useEffect, useState } from "react";
import { ContextBuilder } from "../components/compose/ContextBuilder";
import { SuggestionsPanel } from "../components/compose/SuggestionsPanel";
import { useWorkspace } from "../hooks/useWorkspace";
import { api } from "../services/api";
import type { EmailGenerateResponse, Settings } from "../types";

export function ReplyPage() {
  const { current } = useWorkspace();
  const [thread, setThread] = useState("");
  const [style, setStyle] = useState("Formal");
  const [extra, setExtra] = useState("");
  const [sources, setSources] = useState<string[]>([
    "architecture",
    "previous_emails",
    "chatgpt_knowledge",
  ]);
  const [useStyle, setUseStyle] = useState(true);
  const [useKb, setUseKb] = useState(true);
  const [analyze, setAnalyze] = useState(true);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [result, setResult] = useState<EmailGenerateResponse | null>(null);
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.settings.get().then(setSettings).catch(console.error);
  }, []);

  const generate = async () => {
    if (!thread.trim()) return;
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await api.emails.reply({
        thread,
        style,
        workspace_id: current?.id,
        context_sources: sources,
        use_style_memory: useStyle,
        use_knowledge_base: useKb,
        extra_instructions: extra || undefined,
        analyze_thread: analyze,
      });
      setResult(res);
      setOutput(res.generated_text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate reply");
    } finally {
      setLoading(false);
    }
  };

  const saveFinal = async () => {
    if (!result) return;
    try {
      await api.emails.saveFinal(result.id, output, true);
      setMessage("Reply saved and added to style memory.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const styles = settings?.available_reply_styles || [
    "Formal",
    "Friendly",
    "Executive",
    "Technical",
  ];

  return (
    <div>
      <h1 className="page-title">Reply to Email</h1>
      <p className="page-desc">
        Paste a full thread. The assistant identifies open questions, action items, and drafts a
        contextual reply.
      </p>

      {error && <div className="error-banner">{error}</div>}
      {message && <div className="success-banner">{message}</div>}

      <div className="grid-2">
        <div className="panel">
          <h3 className="panel-title">Email Thread</h3>
          <textarea
            className="textarea tall"
            value={thread}
            onChange={(e) => setThread(e.target.value)}
            placeholder="Paste the full email thread here…"
          />
          <div style={{ marginTop: "0.85rem" }}>
            <label className="field-label">Reply style</label>
            <select
              className="select"
              value={style}
              onChange={(e) => setStyle(e.target.value)}
            >
              {styles.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div style={{ marginTop: "0.85rem" }}>
            <label className="field-label">Extra instructions</label>
            <textarea
              className="textarea"
              style={{ minHeight: 70 }}
              value={extra}
              onChange={(e) => setExtra(e.target.value)}
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
            <label className="chip">
              <input
                type="checkbox"
                checked={analyze}
                onChange={(e) => setAnalyze(e.target.checked)}
              />{" "}
              Analyze thread
            </label>
          </div>
          <div className="btn-row" style={{ marginTop: "1rem" }}>
            <button className="btn btn-primary" onClick={generate} disabled={loading}>
              {loading && <span className="spinner" />}
              Generate Reply
            </button>
          </div>
        </div>

        <div>
          <div className="panel">
            <h3 className="panel-title">Draft Reply</h3>
            <textarea
              className="textarea output"
              value={output}
              onChange={(e) => setOutput(e.target.value)}
              placeholder="Reply draft will appear here…"
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
          <SuggestionsPanel
            suggestions={result?.suggestions}
            analysis={result?.thread_analysis}
          />
        </div>
      </div>
    </div>
  );
}
