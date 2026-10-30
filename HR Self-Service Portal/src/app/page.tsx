import { redirect } from "next/navigation";
import { getCurrentSession, hasSessionCookie } from "@/server/auth/session";

export default async function HomePage() {
  const session = await getCurrentSession();
  if (!session) {
    if (await hasSessionCookie()) redirect("/session/clear");
    redirect("/login");
  }
  redirect(session.user.role === "ADMINISTRATOR" ? "/admin" : "/dashboard");
}
