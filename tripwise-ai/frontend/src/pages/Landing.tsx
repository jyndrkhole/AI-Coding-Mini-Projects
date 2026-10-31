import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";

type Destination = {
  slug: string;
  name: string;
  state: string;
  destination_type: string;
  best_season: string;
  image_url: string;
  budget_min: number;
  budget_max: number;
};

const types = ["Beach", "Hills", "Heritage", "Adventure", "Nature"];

export function Landing() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("Plan a 5-day family trip to Kerala under ₹60,000.");
  const [places, setPlaces] = useState<Destination[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Destination[]>("/api/destinations")
      .then((rows) => setPlaces(rows.slice(0, 6)))
      .catch((err: Error) => setError(err.message));
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    navigate(`/advisor?q=${encodeURIComponent(query)}`);
  }

  return (
    <div className="-mx-4 -mt-8">
      <section className="relative min-h-[78vh] overflow-hidden">
        <img
          src="https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=2000&q=80"
          alt="Mist over a mountain ridge"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-ink/80 via-ink/55 to-ink/20" />
        <div className="relative mx-auto flex min-h-[78vh] max-w-6xl flex-col justify-center px-4 py-16 text-cream">
          <p className="font-display text-2xl text-cream">TripWise AI</p>
          <h1 className="mt-8 max-w-2xl font-display text-5xl leading-tight md:text-6xl">
            Your Next Journey Starts with a Smarter Plan.
          </h1>
          <p className="mt-4 max-w-xl text-lg text-cream/85">
            Tell us where you want to go, what you love, and your budget. Your AI travel advisor will take care of the planning.
          </p>
          <form onSubmit={submit} className="mt-8 max-w-2xl rounded-3xl bg-card p-3 text-ink shadow-card">
            <label className="px-2 text-xs uppercase tracking-wide text-ink/50" htmlFor="plan">
              Ask TripWise
            </label>
            <div className="mt-1 flex flex-col gap-2 sm:flex-row">
              <input
                id="plan"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="w-full rounded-2xl border border-line bg-cream px-4 py-3 outline-none"
              />
              <button className="rounded-2xl bg-teal px-5 py-3 font-medium text-white">Plan My Trip</button>
            </div>
          </form>
        </div>
      </section>
      <section className="mx-auto max-w-6xl px-4 py-14">
        <h2 className="font-display text-3xl">Popular destinations</h2>
        <p className="mt-1 text-ink/70">Demonstration catalogue. Prices are sample estimates, not live fares.</p>
        {error && <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-red-800">{error}</p>}
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {places.map((place) => (
            <Link key={place.slug} to={`/destinations/${place.slug}`} className="overflow-hidden rounded-3xl bg-card shadow-card">
              <img src={place.image_url} alt="" className="h-44 w-full object-cover" />
              <div className="p-4">
                <p className="text-xs uppercase tracking-wide text-teal">{place.destination_type}</p>
                <h3 className="font-display text-2xl">{place.name}</h3>
                <p className="text-sm text-ink/70">{place.state} · {place.best_season}</p>
              </div>
            </Link>
          ))}
        </div>
        <h2 className="mt-14 font-display text-3xl">Explore by travel type</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          {types.map((type) => (
            <Link key={type} to={`/destinations?type=${type}`} className="rounded-full border border-line bg-card px-4 py-2">
              {type}
            </Link>
          ))}
        </div>
        <h2 className="mt-14 font-display text-3xl">How TripWise AI works</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {[
            ["Notebook", "Chroma retrieves seasonal notes and safety tips. It does not store prices."],
            ["MCP server", "Lookup, the destination list, and exact rupee maths live in a separate server."],
            ["Two chains", "A tool computes the figure. One chain explains it. The next says GO or NOT YET."],
          ].map(([title, copy]) => (
            <article key={title} className="rounded-3xl bg-card p-5 shadow-card">
              <h3 className="font-display text-2xl">{title}</h3>
              <p className="mt-2 text-ink/75">{copy}</p>
            </article>
          ))}
        </div>
        <footer className="mt-14 flex flex-wrap gap-4 border-t border-line py-6 text-sm text-ink/60">
          <span>About</span>
          <span>Contact</span>
          <span>Privacy</span>
          <span>Terms</span>
        </footer>
      </section>
    </div>
  );
}
