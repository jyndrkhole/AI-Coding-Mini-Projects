import { type FormEvent, useState } from "react";
import { APP_NAME } from "../constants";
import { api, ApiError } from "../services/api";
import type { PortalSession } from "../types";
import { ThemeToggle } from "../components/ThemeToggle";

export function LoginPage({ onLoggedIn }: { onLoggedIn: (session: PortalSession) => void }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const session = await api.login(username, password);
      onLoggedIn(session);
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-shell">
      <form className="card panel login-card" onSubmit={(event) => void submit(event)}>
        <div className="login-card-head">
          <p className="brand-kicker">Application Status</p>
          <h1>{APP_NAME}</h1>
        </div>
        {error ? <div className="flash error">{error}</div> : null}
        <label className="field">
          Username
          <input
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label className="field">
          Password
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <div className="login-actions">
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <ThemeToggle />
        </div>
      </form>
    </div>
  );
}
