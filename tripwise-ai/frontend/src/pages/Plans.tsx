import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/Auth";
import { api, inr } from "../lib/api";

export function Itinerary() {
  const { user } = useAuth();
  const [destination, setDestination] = useState("Kerala");
  const [days, setDays] = useState(5);
  const [people, setPeople] = useState(4);
  const [trip, setTrip] = useState<any>(null);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!user) return;
    setError("");
    try {
      setTrip(await api("/api/itineraries/generate", {
        method: "POST",
        body: JSON.stringify({ destination, days, people, save: true }),
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not build the itinerary");
    }
  }

  async function regenerate(dayId: number) {
    const updated = await api<any>(`/api/itineraries/${dayId}/regenerate`, { method: "POST" });
    setTrip({
      ...trip,
      days: trip.days.map((day: any) => (day.id === dayId ? updated : day)),
    });
  }

  if (!user) return <p>Sign in to save an itinerary. <Link className="text-teal" to="/login">Sign in</Link></p>;

  return (
    <div>
      <h1 className="font-display text-4xl">Itinerary</h1>
      <p className="mt-2 text-ink/70">Days are built from stored attractions. Regenerating one day leaves the others alone.</p>
      <form onSubmit={submit} className="mt-4 flex flex-wrap gap-2">
        <input className="rounded-2xl border border-line bg-card px-3 py-2" value={destination} onChange={(e) => setDestination(e.target.value)} aria-label="Destination" />
        <input type="number" className="w-24 rounded-2xl border border-line bg-card px-3 py-2" value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Days" />
        <input type="number" className="w-24 rounded-2xl border border-line bg-card px-3 py-2" value={people} onChange={(e) => setPeople(Number(e.target.value))} aria-label="People" />
        <button className="rounded-2xl bg-teal px-4 text-white">Generate</button>
      </form>
      {error && <p className="mt-4 text-red-700">{error}</p>}
      <div className="mt-6 space-y-3">
        {trip?.days?.map((day: any) => (
          <article key={day.id} className="rounded-3xl bg-card p-4 shadow-card">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-display text-2xl">{day.title}</h2>
              <button className="text-sm text-teal" onClick={() => regenerate(day.id)}>Regenerate day</button>
            </div>
            {["morning", "afternoon", "evening"].map((slot) => (
              <p key={slot} className="mt-2 text-sm"><strong className="capitalize">{slot}.</strong> {day.activities[slot]?.title} — {day.activities[slot]?.detail}</p>
            ))}
            <p className="mt-2 text-sm text-ink/60">Sample activity cost {inr(day.estimated_cost)}. {day.activities.tip}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

export function Trips() {
  const { user } = useAuth();
  const [trips, setTrips] = useState<any[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    api<any[]>("/api/trips").then(setTrips).catch((err: Error) => setError(err.message));
  }, [user]);

  if (!user) return <p>Sign in to see your trips.</p>;
  return (
    <div>
      <h1 className="font-display text-4xl">Your trips</h1>
      {error && <p className="mt-3 text-red-700">{error}</p>}
      {trips?.length === 0 && <p className="mt-4">No saved trips yet. Generate an itinerary to start one.</p>}
      <div className="mt-4 grid gap-3">
        {trips?.map((trip) => (
          <article key={trip.id} className="rounded-3xl bg-card p-4 shadow-card">
            <h2 className="font-display text-2xl">{trip.title}</h2>
            <p className="text-sm text-ink/70">{trip.traveler_count} travellers · {trip.days?.length || 0} days · {trip.status}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
