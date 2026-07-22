import { useEffect, useRef, useState } from "react";
import { useWorkspace } from "../hooks/useWorkspace";
import { api } from "../services/api";
import type { ChatMessage } from "../types";

export function ChatPage() {
  const { current } = useWorkspace();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [useKb, setUseKb] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!current) return;
    api.chat
      .history(current.id)
      .then(setMessages)
      .catch((e) => setError(e.message));
  }, [current?.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim()) return;
    const userText = input.trim();
    setInput("");
    setLoading(true);
    setError("");
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        role: "user",
        content: userText,
        created_at: new Date().toISOString(),
      },
    ]);
    try {
      const res = await api.chat.send({
        message: userText,
        workspace_id: current?.id,
        use_knowledge_base: useKb,
      });
      setMessages((prev) => [...prev, res.reply]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="page-title">Chat</h1>
      <p className="page-desc">
        Ask questions against your workspace knowledge — architecture decisions, prior emails, and
        notes.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="panel chat-window">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="empty">Start a conversation about your projects or emails.</div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`chat-bubble ${m.role}`}>
              {m.content}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <div className="btn-row" style={{ marginBottom: "0.65rem" }}>
          <label className="chip">
            <input
              type="checkbox"
              checked={useKb}
              onChange={(e) => setUseKb(e.target.checked)}
            />{" "}
            Use knowledge base
          </label>
        </div>
        <div className="chat-input-row">
          <input
            className="input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="How did I explain Kubernetes HA to clients?"
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          />
          <button className="btn btn-primary" onClick={send} disabled={loading}>
            {loading ? <span className="spinner" /> : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
