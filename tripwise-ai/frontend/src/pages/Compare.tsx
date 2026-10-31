import { FormEvent, useState } from "react";
import { api, inr } from "../lib/api";

export function Compare() {
  const [places, setPlaces] = useState("Goa, Gokarna, Alibaug");
  const [people, setPeople] = useState(2);
  const [nights, setNights] = useState(3);
  const [rows, setRows] = useState<any[]>([]);
  const [missing, setMissing] = useState<any[]>([]);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const data = await api<{ rows: any[]; missing: any[] }>("/api/budget/compare", {
        method: "POST",
        body: JSON.stringify({
          places: places.split(",").map((item) => item.trim()).filter(Boolean),
          people,
          nights,
        }),
      });
      setRows(data.rows);
      setMissing(data.missing);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compare failed");
    }
  }

  return (
    <div>
      <h1 className="font-display text-4xl">Compare</h1>
      <p className="mt-2 text-ink/70">Up to three destinations. Every rupee comes from the MCP cost tool.</p>
      <form onSubmit={submit} className="mt-4 flex flex-wrap gap-2">
        <input className="min-w-64 flex-1 rounded-2xl border border-line bg-card px-3 py-2" value={places} onChange={(e) => setPlaces(e.target.value)} aria-label="Places" />
        <input type="number" className="w-24 rounded-2xl border border-line bg-card px-3 py-2" value={people} onChange={(e) => setPeople(Number(e.target.value))} aria-label="People" />
        <input type="number" className="w-24 rounded-2xl border border-line bg-card px-3 py-2" value={nights} onChange={(e) => setNights(Number(e.target.value))} aria-label="Nights" />
        <button className="rounded-2xl bg-deep px-4 text-cream">Compare</button>
      </form>
      {error && <p className="mt-4 text-red-700">{error}</p>}
      {missing.length > 0 && <p className="mt-4 text-sm">Not in the catalogue: {missing.map((item) => item.place).join(", ")}</p>}
      {rows.length > 0 && (
        <div className="mt-6 overflow-auto rounded-3xl bg-card shadow-card">
          <table className="w-full text-left text-sm">
            <thead className="text-ink/60">
              <tr>
                {["Place", "Type", "Season", "Stay", "Travel", "Per person", "Couple", "Family"].map((heading) => <th key={heading} className="px-3 py-3">{heading}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.place_id} className="border-t border-line">
                  <td className="px-3 py-3 font-medium">{row.name}</td>
                  <td className="px-3 py-3">{row.trip_type}</td>
                  <td className="px-3 py-3">{row.best_months}</td>
                  <td className="px-3 py-3">{row.stay_name}</td>
                  <td className="px-3 py-3">{row.travel_mode}</td>
                  <td className="px-3 py-3">{inr(row.total_per_person)}</td>
                  <td className="px-3 py-3">{row.couple_fit || "—"}</td>
                  <td className="px-3 py-3">{row.family_fit || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 text-xs text-ink/50">Couple and family fit are catalogue labels, not a live score. Costs are demonstration estimates.</p>
    </div>
  );
}
