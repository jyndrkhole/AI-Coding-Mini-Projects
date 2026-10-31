import { useEffect, useState } from "react";
import { api } from "../lib/api";

export function Admin() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<any>("/api/admin/dashboard").then(setData).catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!data) return <p>Loading the admin desk…</p>;
  const cards = [
    ["Travellers", data.users],
    ["Destinations", data.destinations],
    ["Trips", data.trips],
    ["Itinerary days", data.itineraries],
    ["Notebook rows", data.knowledge_documents],
    ["Chroma passages", data.chroma_documents],
  ];
  return (
    <div>
      <h1 className="font-display text-4xl">Admin</h1>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {cards.map(([label, value]) => (
          <article key={String(label)} className="rounded-3xl bg-card p-4 shadow-card">
            <p className="text-sm text-ink/60">{label}</p>
            <p className="font-display text-4xl">{value}</p>
          </article>
        ))}
      </div>
      <h2 className="mt-8 font-display text-2xl">Recent trips</h2>
      <ul className="mt-2 space-y-1 text-sm">
        {data.recent_trips.map((trip: any) => <li key={trip.id}>{trip.title}</li>)}
      </ul>
    </div>
  );
}
