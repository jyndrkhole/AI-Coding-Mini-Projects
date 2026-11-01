import { FormEvent, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/Auth";
import { api, inr } from "../lib/api";

type Card = {
  slug: string;
  name: string;
  state: string;
  destination_type: string;
  best_season: string;
  image_url: string;
  budget_min: number;
  budget_max: number;
};

export function Destinations() {
  const [params, setParams] = useSearchParams();
  const [rows, setRows] = useState<Card[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const type = params.get("audience") || params.get("type") || "";
  const q = params.get("q") || "";
  const sort = params.get("sort") || "name";

  useEffect(() => {
    setLoading(true);
    const query = new URLSearchParams();
    if (type) query.set("audience", type);
    if (q) query.set("q", q);
    if (sort) query.set("sort", sort);
    api<Card[]>(`/api/destinations?${query.toString()}`)
      .then(setRows)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [type, q, sort]);

  return (
    <div>
      <h1 className="font-display text-4xl">Discover</h1>
      <div className="mt-4 flex flex-wrap gap-2">
        <input
          defaultValue={q}
          placeholder="Search Kerala, hills, beach..."
          className="rounded-full border border-line bg-card px-4 py-2"
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              const next = new URLSearchParams(params);
              next.set("q", (event.target as HTMLInputElement).value);
              setParams(next);
            }
          }}
        />
        {["", "Beach", "Hills", "Heritage", "Adventure", "Nature", "wildlife", "spiritual", "family", "romantic", "weekend", "road"].map((item) => (
          <button
            key={item || "all"}
            className={`rounded-full px-3 py-1.5 text-sm ${type === item ? "bg-deep text-cream" : "bg-card"}`}
            onClick={() => {
              const next = new URLSearchParams(params);
              if (item) next.set("audience", item);
              else next.delete("audience");
              next.delete("type");
              setParams(next);
            }}
          >
            {item || "All"}
          </button>
        ))}
        <select
          className="rounded-full border border-line bg-card px-3 py-1.5 text-sm"
          value={params.get("sort") || "name"}
          onChange={(event) => {
            const next = new URLSearchParams(params);
            next.set("sort", event.target.value);
            setParams(next);
          }}
          aria-label="Sort"
        >
          <option value="name">Name</option>
          <option value="budget">Budget</option>
          <option value="duration">Duration</option>
        </select>
      </div>
      {loading && <p className="mt-6">Loading destinations…</p>}
      {error && <p className="mt-6 text-red-700">{error}</p>}
      {!loading && rows.length === 0 && <p className="mt-6">No destinations match that filter.</p>}
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map((place) => (
          <Link key={place.slug} to={`/destinations/${place.slug}`} className="overflow-hidden rounded-3xl bg-card shadow-card">
            <img src={place.image_url} alt="" className="h-40 w-full object-cover" />
            <div className="p-4">
              <p className="text-xs uppercase text-teal">{place.destination_type}</p>
              <h2 className="font-display text-2xl">{place.name}</h2>
              <p className="text-sm text-ink/70">{place.state} · {place.best_season}</p>
              <p className="mt-2 text-sm">{inr(place.budget_min)} – {inr(place.budget_max)} per person, sample range</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function DestinationDetail() {
  const { slug = "" } = useParams();
  const { user } = useAuth();
  const [place, setPlace] = useState<any>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api<any>(`/api/destinations/${slug}`).then(setPlace).catch((err: Error) => setError(err.message));
  }, [slug]);

  useEffect(() => {
    if (!user || !place) return;
    api<any[]>("/api/me/saved")
      .then((rows) => setSaved(rows.some((item) => item.id === place.id)))
      .catch(() => setSaved(false));
  }, [user, place]);

  async function toggleSave(event: FormEvent) {
    event.preventDefault();
    if (!place) return;
    if (saved) {
      await api(`/api/destinations/${place.id}/save`, { method: "DELETE" });
      setSaved(false);
    } else {
      await api(`/api/destinations/${place.id}/save`, { method: "POST" });
      setSaved(true);
    }
  }

  if (error) return <p className="text-red-700">{error}</p>;
  if (!place) return <p>Loading…</p>;
  return (
    <article>
      <img src={place.image_url} alt="" className="h-72 w-full rounded-3xl object-cover" />
      <p className="mt-4 text-xs uppercase text-teal">{place.destination_type} · {place.state}</p>
      <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
        <h1 className="font-display text-5xl">{place.name}</h1>
        {user ? (
          <button className="rounded-full border border-line bg-card px-4 py-2 text-sm" onClick={toggleSave}>
            {saved ? "Saved" : "Save destination"}
          </button>
        ) : (
          <Link to="/login" className="text-sm text-teal">Sign in to save</Link>
        )}
      </div>
      <p className="mt-3 max-w-3xl text-lg text-ink/80">{place.description}</p>
      <p className="mt-2 text-sm text-ink/60">Best season {place.best_season}. Ideal stay {place.ideal_duration_days} days. Sample budget {inr(place.budget_min)}–{inr(place.budget_max)} per person.</p>
      <p className="mt-2 text-sm">Family {place.family_fit} · Couple {place.couple_fit} · Adventure {place.adventure_fit}. These are catalogue labels.</p>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <section className="rounded-3xl bg-card p-4 shadow-card">
          <h2 className="font-display text-2xl">Sample stay</h2>
          {place.accommodations.map((stay: any) => (
            <p key={stay.id} className="mt-2">{stay.name} · {inr(stay.price_per_night)} / night · {stay.source}</p>
          ))}
        </section>
        <section className="rounded-3xl bg-card p-4 shadow-card">
          <h2 className="font-display text-2xl">Notes</h2>
          {place.tips.map((tip: any) => (
            <p key={tip.id} className="mt-2 text-sm"><strong>{tip.title}.</strong> {tip.content}</p>
          ))}
        </section>
      </div>
      <h2 className="mt-8 font-display text-3xl">Attractions</h2>
      <ul className="mt-3 space-y-2">
        {place.attractions.map((item: any) => (
          <li key={item.id} className="rounded-2xl bg-card px-4 py-3">{item.name} · {item.ideal_duration} · sample {inr(item.estimated_cost)}</li>
        ))}
      </ul>
      <h2 className="mt-8 font-display text-3xl">Nearby</h2>
      {place.nearby?.length ? (
        <ul className="mt-3 flex flex-wrap gap-2">
          {place.nearby.map((item: any) => (
            <li key={item.id}>
              <Link className="rounded-full bg-card px-3 py-1.5 text-sm shadow-card" to={`/destinations/${item.slug}`}>{item.name}</Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-ink/60">No nearby places are stored for this destination.</p>
      )}
    </article>
  );
}

