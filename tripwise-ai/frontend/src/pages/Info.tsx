export function About() {
  return (
    <article className="max-w-2xl">
      <h1 className="font-display text-4xl">About</h1>
      <p className="mt-3 text-ink/80">TripWise AI plans trips from a stored destination catalogue and a travel notebook. Prices are demonstration estimates. The model explains them. Python does the arithmetic.</p>
    </article>
  );
}

export function Contact() {
  return (
    <article className="max-w-2xl">
      <h1 className="font-display text-4xl">Contact</h1>
      <p className="mt-3 text-ink/80">This is a local study build. There is no support desk and no live booking line. Use the advisor for catalogue questions.</p>
    </article>
  );
}

export function Privacy() {
  return (
    <article className="max-w-2xl">
      <h1 className="font-display text-4xl">Privacy</h1>
      <p className="mt-3 text-ink/80">Accounts, saved trips, and chat sessions stay in the local SQLite file for the signed-in user. One traveller cannot read another traveller’s trips or conversations.</p>
    </article>
  );
}

export function Terms() {
  return (
    <article className="max-w-2xl">
      <h1 className="font-display text-4xl">Terms</h1>
      <p className="mt-3 text-ink/80">Catalogue prices, stays, and activity costs are samples for this project. They are not offers, availability, or current fares. Check a live source before you travel.</p>
    </article>
  );
}
