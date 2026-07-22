import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { StyleExample } from "../types";

export function StylePage() {
  const [examples, setExamples] = useState<StyleExample[]>([]);
  const [content, setContent] = useState("");
  const [greeting, setGreeting] = useState("");
  const [signOff, setSignOff] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = () => api.style.list().then(setExamples);

  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, []);

  const add = async () => {
    if (!content.trim()) return;
    try {
      await api.style.add({
        content,
        greeting: greeting || undefined,
        sign_off: signOff || undefined,
        notes: notes || undefined,
      });
      setContent("");
      setGreeting("");
      setSignOff("");
      setNotes("");
      setMessage("Style example saved. Future emails will imitate this voice.");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const remove = async (id: number) => {
    await api.style.delete(id);
    await refresh();
  };

  return (
    <div>
      <h1 className="page-title">Writing Style Memory</h1>
      <p className="page-desc">
        Store emails you finally sent, preferred greetings, and sign-offs. The assistant gradually
        mirrors your communication style.
      </p>
      {error && <div className="error-banner">{error}</div>}
      {message && <div className="success-banner">{message}</div>}

      <div className="grid-2">
        <div className="panel">
          <h3 className="panel-title">Add Style Example</h3>
          <textarea
            className="textarea tall"
            placeholder="Paste a final email you sent…"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <div className="grid-2" style={{ marginTop: "0.75rem" }}>
            <div>
              <label className="field-label">Preferred greeting</label>
              <input
                className="input"
                value={greeting}
                onChange={(e) => setGreeting(e.target.value)}
                placeholder="Hi team,"
              />
            </div>
            <div>
              <label className="field-label">Preferred sign-off</label>
              <input
                className="input"
                value={signOff}
                onChange={(e) => setSignOff(e.target.value)}
                placeholder="Best regards,"
              />
            </div>
          </div>
          <div style={{ marginTop: "0.75rem" }}>
            <label className="field-label">Notes</label>
            <input
              className="input"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <button className="btn btn-primary" style={{ marginTop: "0.85rem" }} onClick={add}>
            Save Example
          </button>
        </div>

        <div className="panel">
          <h3 className="panel-title">Stored Examples ({examples.length})</h3>
          {examples.length === 0 ? (
            <div className="empty">No style examples yet. Save a final email from Compose.</div>
          ) : (
            <div className="list">
              {examples.map((ex) => (
                <div key={ex.id} className="list-item">
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
                    <div>
                      <h4>{ex.category}</h4>
                      <p style={{ whiteSpace: "pre-wrap" }}>{ex.content.slice(0, 280)}</p>
                      {(ex.greeting || ex.sign_off) && (
                        <p style={{ marginTop: "0.4rem" }}>
                          {ex.greeting ? `Greeting: ${ex.greeting}` : ""}{" "}
                          {ex.sign_off ? `· Sign-off: ${ex.sign_off}` : ""}
                        </p>
                      )}
                    </div>
                    <button className="btn btn-danger" onClick={() => remove(ex.id)}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
