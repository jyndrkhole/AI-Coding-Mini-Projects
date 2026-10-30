import { redirect } from "next/navigation";
import { getCurrentSession, hasSessionCookie } from "./session";

export async function requireUser() {
  const session = await getCurrentSession();
  if (!session) {
    if (await hasSessionCookie()) redirect("/session/clear");
    redirect("/login");
  }
  return session;
}

export async function requireAdmin() {
  const session = await requireUser();
  if (session.user.role !== "ADMINISTRATOR") redirect("/dashboard");
  return session;
}
