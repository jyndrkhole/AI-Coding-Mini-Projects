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
  "What should we do in Hampi in December?",
];

type Trace = { name: string; args: Record<string, unknown>; result: unknown; is_error: boolean };
type Session = { id: number; session_title: string };

const toolLabels: Record<string, string> = {
  list_destinations: "the catalogue",
  db_lookup: "stored prices",
  compute_trip_cost: "the cost",
  get_prompt: "the trip question",
  search_destinations: "the catalogue",
  get_destination_details: "the destination",
  get_nearby_destinations: "nearby places",
  lookup_accommodation: "sample stays",
  search_attractions: "attractions",
  get_destination_prices: "stored prices",
  retrieve_travel_knowledge: "the notebook",
  search_seasonal_tips: "seasonal notes",
  search_travel_safety_information: "safety notes",
  generate_daywise_itinerary: "the day plan",
  estimate_activity_cost: "activity costs",
  calculate_stay_share: "the stay share",
  calculate_budget_buffer: "the buffer",
  compare_destination_costs: "the comparison",
  ask_local_guide: "the local guide",
};

type MemoryReport = { action: string; type: string; text: string };
type Memory = { facts: Record<string, string>; episodes: string[]; rules: string[] };
type SavedMemory = { report: MemoryReport[]; memory: Memory };

function toolLabel(name: string) {
  return toolLabels[name] || name.replaceAll("_", " ");
}

export function Advisor() {
  const { user } = useAuth();
  const [params] = useSearchParams();
  const [message, setMessage] = useState(params.get("q") || examples[1]);
  const [reply, setReply] = useState("");
  const [trace, setTrace] = useState<Trace[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [memory, setMemory] = useState<Memory>({ facts: {}, episodes: [], rules: [] });
  const [memoryNote, setMemoryNote] = useState("");

  useEffect(() => {
    const q = params.get("q");
    if (q) setMessage(q);
  }, [params]);

  useEffect(() => {
    if (!user) return;
    api<Session[]>("/api/advisor/sessions").then(setSessions).catch(() => undefined);
    api<Memory>("/api/advisor/memory").then(setMemory).catch(() => undefined);
  }, [user, sessionId]);

  async function openSession(id: number) {
    const data = await api<{ messages: { role: string; content: string }[] }>(`/api/advisor/sessions/${id}`);
    const last = [...data.messages].reverse().find((item) => item.role === "assistant");
    setSessionId(id);
    setReply(last?.content || "");
    setTrace([]);
  }

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

  async function saveMemory() {
    if (!sessionId) return;
    setLoading(true);
    setError("");
    try {
      const data = await api<SavedMemory>(`/api/advisor/sessions/${sessionId}/memory`, { method: "POST" });
      setMemory(data.memory);
      const added = (data.report || []).filter((item) => item.action !== "SKIP").length;
      setMemoryNote(added ? `Saved ${added} item${added === 1 ? "" : "s"} for the next chat.` : "Nothing new was worth keeping.");
      setSessionId(null);
      setReply("");
      setTrace([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Memory could not be saved");
    } finally {
      setLoading(false);
    }
  }

  async function forgetMemory() {
    setLoading(true);
    setError("");
    try {
      const data = await api<Memory>("/api/advisor/memory", { method: "DELETE" });
      setMemory(data);
      setMemoryNote("Long-term memory for this account was cleared.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Memory could not be cleared");
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
        <p className="mt-2 text-sm text-ink/70">The model reads the notebook. Prices and arithmetic go through the catalogue. Local tips come from the guide.</p>
        <div className="mt-5">
          <h2 className="text-xs uppercase tracking-wide text-ink/50">Your conversations</h2>
          <button className="mt-2 text-sm text-teal" onClick={() => { setSessionId(null); setReply(""); setTrace([]); }}>New conversation</button>
          <div className="mt-2 space-y-2">
            {sessions.length === 0 && <p className="text-sm text-ink/50">No saved chats yet.</p>}
            {sessions.map((session) => (
              <button key={session.id} className="block w-full rounded-2xl bg-card px-3 py-2 text-left text-sm shadow-card" onClick={() => openSession(session.id)}>
                {session.session_title}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-6">
          <h2 className="text-xs uppercase tracking-wide text-ink/50">Try asking</h2>
          <div className="mt-2 space-y-2">
            {examples.map((example) => (
              <button key={example} className="block w-full rounded-2xl border border-line bg-cream px-3 py-2 text-left text-sm" onClick={() => { setMessage(example); submit(undefined, example); }}>
                {example}
              </button>
            ))}
          </div>
        </div>
      </aside>
      <section className="rounded-3xl bg-card p-5 shadow-card">
        <form onSubmit={submit} className="flex flex-col gap-3">
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} rows={4} className="w-full rounded-2xl border border-line bg-cream px-3 py-2" />
          <div className="flex flex-wrap gap-2">
            <button disabled={loading} className="rounded-2xl bg-deep px-4 py-3 text-cream disabled:opacity-60">
              {loading ? "Working…" : "Send"}
            </button>
            <button type="button" disabled={loading || !sessionId} onClick={saveMemory} className="rounded-2xl border border-line px-4 py-3 text-sm disabled:opacity-50">
              End chat and save to memory
            </button>
            <button type="button" disabled={loading} onClick={forgetMemory} className="rounded-2xl border border-line px-4 py-3 text-sm disabled:opacity-50">
              Forget everything
            </button>
          </div>
        </form>
        {error && <p className="mt-4 rounded-2xl bg-red-50 px-3 py-2 text-red-800">{error}</p>}
        {reply && (
          <div className="prose-trip mt-5 rounded-2xl bg-cream p-4">
            <ReactMarkdown>{reply}</ReactMarkdown>
          </div>
        )}
        {trace.length > 0 && (
          <p className="mt-3 text-xs text-ink/50">
            {trace.some((item) => item.is_error) ? "A lookup failed. " : "Checked "}
            {[...new Set(trace.map((item) => toolLabel(item.name)))].join(", ")}.
          </p>
        )}
        <div className="mt-6 rounded-2xl border border-line bg-cream p-4">
          <h2 className="text-xs uppercase tracking-wide text-ink/50">What this account remembers</h2>
          {memoryNote && <p className="mt-2 text-sm">{memoryNote}</p>}
          {Object.keys(memory.facts).length === 0 && memory.episodes.length === 0 && memory.rules.length === 0 && (
            <p className="mt-2 text-sm text-ink/60">Nothing saved yet. End a chat to keep facts, past trips, and planning rules.</p>
          )}
          {Object.keys(memory.facts).length > 0 && (
            <ul className="mt-3 space-y-1 text-sm">
              {Object.entries(memory.facts).map(([key, value]) => (
                <li key={key}><span className="text-ink/50">{key}: </span>{value}</li>
              ))}
            </ul>
          )}
          {memory.episodes.length > 0 && (
            <ul className="mt-3 space-y-1 text-sm">
              {memory.episodes.map((item) => <li key={item}>{item}</li>)}
            </ul>
          )}
          {memory.rules.length > 0 && (
            <ul className="mt-3 space-y-1 text-sm">
              {memory.rules.map((item) => <li key={item}>{item}</li>)}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
