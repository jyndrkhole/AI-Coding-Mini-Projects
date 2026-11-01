import { FormEvent, useEffect, useState } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

export function Admin() {
  const [data, setData] = useState<any>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [places, setPlaces] = useState<any[]>([]);
  const [placeId, setPlaceId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    const [dashboard, knowledge, people, catalogue] = await Promise.all([
      api<any>("/api/admin/dashboard"),
      api<any[]>("/api/admin/knowledge"),
      api<any[]>("/api/admin/users"),
      api<any[]>("/api/admin/destinations"),
    ]);
    setData(dashboard);
    setDocs(knowledge);
    setUsers(people);
    setPlaces(catalogue);
    setPlaceId((current) => current ?? catalogue[0]?.id ?? null);
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  const place = places.find((item) => item.id === placeId);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setNotice("");
    await api("/api/admin/knowledge/upload", { method: "POST", body: form });
    setNotice("Document indexed.");
    event.currentTarget.reset();
    await load();
  }

  async function savePlace(event: FormEvent) {
    event.preventDefault();
    if (!place) return;
    await api(`/api/admin/destinations/${place.id}`, {
      method: "PUT",
      body: JSON.stringify({
        description: place.description,
        best_season: place.best_season,
        family_fit: place.family_fit,
        couple_fit: place.couple_fit,
        adventure_fit: place.adventure_fit,
        pros: place.pros,
        cons: place.cons,
      }),
    });
    setNotice("Destination saved.");
  }

  function patchPlace(fields: Record<string, string>) {
    setPlaces(places.map((item) => (item.id === placeId ? { ...item, ...fields } : item)));
  }

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
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-4xl">Admin</h1>
        {notice && <p className="mt-2 text-sm text-teal">{notice}</p>}
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {cards.map(([label, value]) => (
            <article key={String(label)} className="rounded-3xl bg-card p-4 shadow-card">
              <p className="text-sm text-ink/60">{label}</p>
              <p className="font-display text-4xl">{value}</p>
            </article>
          ))}
        </div>
        {data.ingestion_errors?.length > 0 && (
          <p className="mt-4 text-sm text-red-700">Ingestion errors: {data.ingestion_errors.map((item: any) => item.title).join(", ")}</p>
        )}
      </div>

      <section>
        <h2 className="font-display text-2xl">Knowledge</h2>
        <form onSubmit={upload} className="mt-3 flex flex-wrap items-end gap-2">
          <Input name="title" placeholder="Title" aria-label="Title" />
          <Input name="destination" placeholder="Destination" aria-label="Destination" />
          <input name="file" type="file" accept=".txt,.md,.pdf,.docx" required className="text-sm" />
          <Button type="submit">Upload</Button>
        </form>
        <ul className="mt-3 space-y-2 text-sm">
          {docs.map((doc) => (
            <li key={doc.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-card px-3 py-2">
              <span>{doc.title} · {doc.ingestion_status} · {doc.chunk_count} chunks{doc.error_message ? ` · ${doc.error_message}` : ""}</span>
              <span className="flex gap-2">
                <button className="text-teal" onClick={async () => { await api(`/api/admin/knowledge/${doc.id}/reindex`, { method: "POST" }); await load(); }}>Re-index</button>
                <button className="text-red-700" onClick={async () => { await api(`/api/admin/knowledge/${doc.id}`, { method: "DELETE" }); await load(); }}>Delete</button>
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl">Catalogue</h2>
        <select className="mt-3 rounded-2xl border border-line bg-card px-3 py-2" value={placeId ?? ""} onChange={(event) => setPlaceId(Number(event.target.value))} aria-label="Destination">
          {places.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        {place && (
          <form onSubmit={savePlace} className="mt-3 grid gap-2">
            <textarea className="rounded-2xl border border-line px-3 py-2" value={place.description} onChange={(event) => patchPlace({ description: event.target.value })} aria-label="Description" />
            <Input value={place.best_season} onChange={(event) => patchPlace({ best_season: event.target.value })} aria-label="Best season" />
            <div className="grid gap-2 sm:grid-cols-3">
              <Input value={place.family_fit} onChange={(event) => patchPlace({ family_fit: event.target.value })} aria-label="Family fit" />
              <Input value={place.couple_fit} onChange={(event) => patchPlace({ couple_fit: event.target.value })} aria-label="Couple fit" />
              <Input value={place.adventure_fit} onChange={(event) => patchPlace({ adventure_fit: event.target.value })} aria-label="Adventure fit" />
            </div>
            <textarea className="rounded-2xl border border-line px-3 py-2" value={place.pros} onChange={(event) => patchPlace({ pros: event.target.value })} aria-label="Pros" />
            <textarea className="rounded-2xl border border-line px-3 py-2" value={place.cons} onChange={(event) => patchPlace({ cons: event.target.value })} aria-label="Cons" />
            <Button type="submit" variant="deep">Save destination</Button>
          </form>
        )}
        {place?.accommodations?.map((stay: any) => (
          <form key={stay.id} className="mt-2 flex flex-wrap gap-2" onSubmit={async (event) => {
            event.preventDefault();
            const price = Number(new FormData(event.currentTarget).get("price"));
            await api(`/api/admin/accommodations/${stay.id}`, { method: "PUT", body: JSON.stringify({ price_per_night: price }) });
            setNotice("Stay price saved.");
          }}>
            <span className="self-center text-sm">{stay.name}</span>
            <Input name="price" type="number" defaultValue={stay.price_per_night} aria-label={`${stay.name} price`} />
            <Button type="submit" variant="outline">Save stay</Button>
          </form>
        ))}
        {place?.attractions?.map((item: any) => (
          <form key={item.id} className="mt-2 flex flex-wrap gap-2" onSubmit={async (event) => {
            event.preventDefault();
            const cost = Number(new FormData(event.currentTarget).get("cost"));
            await api(`/api/admin/attractions/${item.id}`, { method: "PUT", body: JSON.stringify({ estimated_cost: cost }) });
            setNotice("Attraction cost saved.");
          }}>
            <span className="self-center text-sm">{item.name}</span>
            <Input name="cost" type="number" defaultValue={item.estimated_cost} aria-label={`${item.name} cost`} />
            <Button type="submit" variant="outline">Save attraction</Button>
          </form>
        ))}
        {place?.tips?.map((tip: any) => (
          <form key={tip.id} className="mt-2 grid gap-2" onSubmit={async (event) => {
            event.preventDefault();
            const content = String(new FormData(event.currentTarget).get("content") || "");
            await api(`/api/admin/tips/${tip.id}`, { method: "PUT", body: JSON.stringify({ content }) });
            setNotice("Tip saved.");
          }}>
            <p className="text-sm font-medium">{tip.title}</p>
            <textarea name="content" defaultValue={tip.content} className="rounded-2xl border border-line px-3 py-2 text-sm" aria-label={tip.title} />
            <Button type="submit" variant="outline">Save tip</Button>
          </form>
        ))}
      </section>

      <section>
        <h2 className="font-display text-2xl">Users</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {users.map((person) => (
            <li key={person.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-card px-3 py-2">
              <span>{person.name} · {person.email} · {person.role}</span>
              <Button variant="outline" onClick={async () => {
                await api(`/api/admin/users/${person.id}/role`, { method: "PUT", body: JSON.stringify({ role: person.role === "admin" ? "user" : "admin" }) });
                await load();
              }}>Toggle role</Button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
