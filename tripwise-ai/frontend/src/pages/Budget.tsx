import { FormEvent, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { api, inr } from "../lib/api";

export function Budget() {
  const [place, setPlace] = useState("Goa");
  const [people, setPeople] = useState(4);
  const [nights, setNights] = useState(3);
  const [budget, setBudget] = useState(12000);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      setData(await api("/api/budget/pipeline", {
        method: "POST",
        body: JSON.stringify({ place, people, nights, budget_per_person: budget }),
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not calculate");
    } finally {
      setLoading(false);
    }
  }

  const tool = data?.tool_result;
  const chart = tool
    ? [
        { name: "Travel", value: data.record.travel_cost_per_person },
        { name: "Stay share", value: tool.stay_share_per_person },
        { name: "Food and fun", value: tool.food_and_fun_per_person },
      ]
    : [];

  return (
    <div>
      <h1 className="font-display text-4xl">Budget pipeline</h1>
      <p className="mt-2 max-w-2xl text-ink/70">Python calls the MCP cost tool first. Chain 1 explains those numbers. Chain 2 reads that explanation and says GO or NOT YET.</p>
      <form onSubmit={submit} className="mt-5 grid gap-3 rounded-3xl bg-card p-4 shadow-card sm:grid-cols-5">
        <input className="rounded-2xl border border-line px-3 py-2" value={place} onChange={(e) => setPlace(e.target.value)} aria-label="Place" />
        <input type="number" className="rounded-2xl border border-line px-3 py-2" value={people} onChange={(e) => setPeople(Number(e.target.value))} aria-label="People" />
        <input type="number" className="rounded-2xl border border-line px-3 py-2" value={nights} onChange={(e) => setNights(Number(e.target.value))} aria-label="Nights" />
        <input type="number" className="rounded-2xl border border-line px-3 py-2" value={budget} onChange={(e) => setBudget(Number(e.target.value))} aria-label="Budget per person" />
        <button className="rounded-2xl bg-teal text-white" disabled={loading}>{loading ? "Running…" : "Run pipeline"}</button>
      </form>
      {error && <p className="mt-4 text-red-700">{error}</p>}
      {tool && (
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          <section className="rounded-3xl bg-card p-4 shadow-card">
            <p className="text-xs uppercase text-teal">Tool</p>
            <h2 className="font-display text-3xl">{inr(tool.total_per_person)}</h2>
            <p>per person · {tool.rooms_needed} rooms · rule {data.rule_decision}</p>
            <p className="text-sm text-ink/60">Money left {inr(tool.money_left_per_person)}. Demonstration estimate.</p>
            <div className="h-40">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={chart} dataKey="value" nameKey="name" innerRadius={40} outerRadius={60}>
                    {chart.map((entry) => <Cell key={entry.name} fill={entry.name === "Travel" ? "#0f6e67" : entry.name === "Stay share" ? "#142033" : "#a67c2d"} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </section>
          <section className="rounded-3xl bg-card p-4 shadow-card">
            <p className="text-xs uppercase text-teal">Chain 1 · explain</p>
            <p className="mt-2 whitespace-pre-wrap text-sm">{data.breakdown || data.chain_error || "The model did not return an explanation."}</p>
          </section>
          <section className="rounded-3xl bg-card p-4 shadow-card">
            <p className="text-xs uppercase text-teal">Chain 2 · decide</p>
            <p className="mt-2 whitespace-pre-wrap text-sm">{data.decision || "Waiting on chain 1."}</p>
          </section>
        </div>
      )}
      <CategoryPlanner />
    </div>
  );
}

function CategoryPlanner() {
  const [people, setPeople] = useState(4);
  const [nights, setNights] = useState(3);
  const [room, setRoom] = useState(3000);
  const [travel, setTravel] = useState(2800);
  const [food, setFood] = useState(800);
  const [local, setLocal] = useState(200);
  const [activities, setActivities] = useState(500);
  const [tickets, setTickets] = useState(200);
  const [shopping, setShopping] = useState(0);
  const [misc, setMisc] = useState(300);
  const [budgetTotal, setBudgetTotal] = useState(60000);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      setResult(await api("/api/budget/calculate", {
        method: "POST",
        body: JSON.stringify({
          people,
          nights,
          room_price_per_night: room,
          travel_per_person: travel,
          food_per_person_per_day: food,
          local_transport_per_person_per_day: local,
          activities_per_person: activities,
          entry_tickets_per_person: tickets,
          shopping_per_person: shopping,
          miscellaneous_per_person: misc,
          budget_total: budgetTotal,
        }),
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not calculate");
    }
  }

  const fields = [
    ["Room / night", room, setRoom],
    ["Travel / person", travel, setTravel],
    ["Food / person / day", food, setFood],
    ["Local transport / day", local, setLocal],
    ["Activities / person", activities, setActivities],
    ["Tickets / person", tickets, setTickets],
    ["Shopping / person", shopping, setShopping],
    ["Miscellaneous / person", misc, setMisc],
  ] as const;

  return (
    <section className="mt-10">
      <h2 className="font-display text-3xl">Category planner</h2>
      <p className="mt-2 max-w-2xl text-sm text-ink/70">Enter the figures yourself or copy them from a catalogue lookup. Python adds them. A 10% buffer is included.</p>
      <form onSubmit={submit} className="mt-4 grid gap-3 rounded-3xl bg-card p-4 shadow-card sm:grid-cols-2 lg:grid-cols-4">
        <input type="number" className="rounded-2xl border border-line px-3 py-2" value={people} onChange={(e) => setPeople(Number(e.target.value))} aria-label="People" />
        <input type="number" className="rounded-2xl border border-line px-3 py-2" value={nights} onChange={(e) => setNights(Number(e.target.value))} aria-label="Nights" />
        {fields.map(([label, value, setter]) => (
          <label key={label} className="text-xs text-ink/60">
            {label}
            <input type="number" className="mt-1 w-full rounded-2xl border border-line px-3 py-2 text-sm text-ink" value={value} onChange={(e) => setter(Number(e.target.value))} />
          </label>
        ))}
        <label className="text-xs text-ink/60">
          Trip budget
          <input type="number" className="mt-1 w-full rounded-2xl border border-line px-3 py-2 text-sm text-ink" value={budgetTotal} onChange={(e) => setBudgetTotal(Number(e.target.value))} />
        </label>
        <button className="rounded-2xl bg-deep text-cream">Calculate categories</button>
      </form>
      {error && <p className="mt-3 text-red-700">{error}</p>}
      {result && (
        <div className="mt-4 rounded-3xl bg-card p-4 shadow-card text-sm">
          <p className="font-display text-3xl">{inr(result.cost_per_person)} per person</p>
          <p>Total {inr(result.total_trip_cost)} · per day {inr(result.cost_per_day)} · buffer {inr(result.buffer_per_person)}</p>
          <p>{result.within_budget ? "Within the trip budget." : "Over the trip budget."} Remaining {inr(result.remaining_budget)}.</p>
          <ul className="mt-2">
            {Object.entries(result.categories_per_person).map(([key, value]) => (
              <li key={key}>{key}: {inr(value as number)}</li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-ink/50">Demonstration arithmetic. These inputs are not live fares.</p>
        </div>
      )}
    </section>
  );
}
