import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/Auth";

export function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("traveler@example.com");
  const [password, setPassword] = useState("Tripwise#Travel1");
  const [error, setError] = useState("");

  useEffect(() => {
    if (user) navigate("/advisor");
  }, [user, navigate]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await login(email, password);
      navigate("/advisor");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in");
    }
  }

  return (
    <div className="mx-auto max-w-md rounded-3xl bg-card p-6 shadow-card">
      <h1 className="font-display text-4xl">Sign in</h1>
      <p className="mt-2 text-sm text-ink/70">Local demonstration accounts. They are not production credentials.</p>
      <form onSubmit={submit} className="mt-6 space-y-3">
        <label className="block text-sm">
          Email
          <input className="mt-1 w-full rounded-2xl border border-line px-3 py-2" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="block text-sm">
          Password
          <input type="password" className="mt-1 w-full rounded-2xl border border-line px-3 py-2" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button className="w-full rounded-2xl bg-teal py-3 text-white">Continue</button>
      </form>
      <div className="mt-4 space-y-2 text-sm">
        <button className="w-full rounded-2xl border border-line py-2" onClick={() => { setEmail("traveler@example.com"); setPassword("Tripwise#Travel1"); }}>
          Use traveller demo
        </button>
        <button className="w-full rounded-2xl border border-line py-2" onClick={() => { setEmail("admin@example.com"); setPassword("Tripwise#Admin1"); }}>
          Use admin demo
        </button>
      </div>
      <Link to="/" className="mt-4 inline-block text-sm text-teal">Back home</Link>
    </div>
  );
}
