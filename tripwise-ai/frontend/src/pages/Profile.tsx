import { FormEvent, useState } from "react";
import { useAuth } from "../context/Auth";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

export function Profile() {
  const { user, updateProfile } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  if (!user) return <p>Sign in to edit your profile.</p>;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await updateProfile(name);
      setMessage("Profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the profile");
    }
  }

  return (
    <form onSubmit={submit} className="max-w-md rounded-3xl bg-card p-5 shadow-card">
      <h1 className="font-display text-4xl">Profile</h1>
      <p className="mt-2 text-sm text-ink/70">{user.email} · {user.role}</p>
      <label className="mt-4 block text-sm">
        Name
        <Input className="mt-1 w-full" value={name} onChange={(event) => setName(event.target.value)} />
      </label>
      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
      {message && <p className="mt-3 text-sm text-teal">{message}</p>}
      <Button className="mt-4" type="submit">Save profile</Button>
    </form>
  );
}
