import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
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
  const type = params.get("type") || "";
  const q = params.get("q") || "";

  useEffect(() => {
    setLoading(true);
    const query = new URLSearchParams();
    if (type) query.set("destination_type", type);
    if (q) query.set("q", q);
    api<Card[]>(`/api/destinations?${query.toString()}`)
      .then(setRows)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [type, q]);

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
        {["", "Beach", "Hills", "Heritage", "Adventure", "Nature"].map((item) => (
          <button
            key={item || "all"}
            className={`rounded-full px-3 py-1.5 text-sm ${type === item ? "bg-deep text-cream" : "bg-card"}`}
            onClick={() => {
              const next = new URLSearchParams(params);
              if (item) next.set("type", item);
              else next.delete("type");
              setParams(next);
            }}
          >
            {item || "All"}
          </button>
        ))}
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
  const [place, setPlace] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<any>(`/api/destinations/${slug}`).then(setPlace).catch((err: Error) => setError(err.message));
  }, [slug]);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!place) return <p>Loading…</p>;
  return (
    <article>
      <img src={place.image_url} alt="" className="h-72 w-full rounded-3xl object-cover" />
      <p className="mt-4 text-xs uppercase text-teal">{place.destination_type} · {place.state}</p>
      <h1 className="font-display text-5xl">{place.name}</h1>
      <p className="mt-3 max-w-3xl text-lg text-ink/80">{place.description}</p>
      <p className="mt-2 text-sm text-ink/60">Best season {place.best_season}. Ideal stay {place.ideal_duration_days} days. Sample budget {inr(place.budget_min)}–{inr(place.budget_max)} per person.</p>
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
    </article>
  );
}
