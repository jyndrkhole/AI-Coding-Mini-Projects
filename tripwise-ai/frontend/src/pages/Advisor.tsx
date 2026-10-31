import { FormEvent, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/Auth";
import { api } from "../lib/api";

const examples = [
  "list",
  "We are 4 friends with ₹12,000 each. Can we do Goa for 3 nights?",
  "/plan Hampi 5 2 6000",
  "Is Manali a good idea in July?",
  "Plan a 5-day family trip to Kerala under ₹60,000.",
  "Suggest destinations near Pune for a 3-day weekend.",
];

type Trace = { name: string; args: Record<string, unknown>; result: unknown; is_error: boolean };

export function Advisor() {
  const { user } = useAuth();
  const [params] = useSearchParams();
  const [message, setMessage] = useState(params.get("q") || examples[1]);
  const [reply, setReply] = useState("");
  const [trace, setTrace] = useState<Trace[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<number | null>(null);

  useEffect(() => {
    const q = params.get("q");
    if (q) setMessage(q);
  }, [params]);

  async function submit(event?: FormEvent, preset?: string) {
    event?.preventDefault();
    if (!user) return;
    const text = preset || message;
    setLoading(true);
    setError("");
    try {
      const data = await api<{ reply: string; tool_trace: Trace[]; session: { id: number } }>("/api/advisor/chat", {
        method: "POST",
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });
      setReply(data.reply);
      setTrace(data.tool_trace || []);
      setSessionId(data.session.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The advisor failed");
    } finally {
      setLoading(false);
    }
  }

  if (!user) {
    return (
      <div className="rounded-3xl bg-card p-6 shadow-card">
        <h1 className="font-display text-4xl">Advisor</h1>
        <p className="mt-2">Sign in with the local traveller account to keep this conversation on your user only.</p>
        <Link to="/login" className="mt-4 inline-block rounded-full bg-teal px-4 py-2 text-white">Sign in</Link>
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
      <aside>
        <h1 className="font-display text-4xl">Advisor</h1>
        <p className="mt-2 text-sm text-ink/70">The model reads the notebook. Prices and arithmetic go through the MCP server.</p>
        <div className="mt-4 space-y-2">
          {examples.map((example) => (
            <button key={example} className="block w-full rounded-2xl bg-card px-3 py-2 text-left text-sm shadow-card" onClick={() => { setMessage(example); submit(undefined, example); }}>
              {example}
            </button>
          ))}
        </div>
      </aside>
      <section className="rounded-3xl bg-card p-5 shadow-card">
        <form onSubmit={submit} className="flex flex-col gap-3">
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} rows={4} className="w-full rounded-2xl border border-line bg-cream px-3 py-2" />
          <button disabled={loading} className="rounded-2xl bg-deep px-4 py-3 text-cream disabled:opacity-60">
            {loading ? "Asking the advisor…" : "Send"}
          </button>
        </form>
        {error && <p className="mt-4 rounded-2xl bg-red-50 px-3 py-2 text-red-800">{error}</p>}
        {reply && (
          <div className="prose-trip mt-5 rounded-2xl bg-cream p-4">
            <ReactMarkdown>{reply}</ReactMarkdown>
          </div>
        )}
        {trace.length > 0 && (
          <div className="mt-4 space-y-2">
            <h2 className="text-sm uppercase tracking-wide text-ink/50">MCP tool trace</h2>
            {trace.map((item, index) => (
              <details key={`${item.name}-${index}`} className="rounded-2xl border border-line px-3 py-2 text-sm">
                <summary>{item.is_error ? "Error · " : ""}{item.name}</summary>
                <pre className="mt-2 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify({ args: item.args, result: item.result }, null, 2)}</pre>
              </details>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
