import { redirect } from "next/navigation";
import { LoginForm } from "@/app/login/login-form";
import { getCurrentSession } from "@/server/auth/session";
import { getOrganization } from "@/server/services/organization";

export const metadata = { title: "Sign in" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const session = await getCurrentSession().catch(() => null);
  if (session) {
    redirect(session.user.role === "ADMINISTRATOR" ? "/admin" : "/dashboard");
  }

  const params = await searchParams;
  let companyName = "Your organization";
  try {
    companyName = (await getOrganization()).companyName;
  } catch {
    companyName = "Your organization";
  }

  const next = params.next && params.next.startsWith("/") && !params.next.startsWith("//") ? params.next : undefined;

  return (
    <main className="grid min-h-full lg:grid-cols-[minmax(0,0.9fr)_minmax(420px,1fr)]">
      <section className="hidden flex-col justify-between bg-brand px-12 py-12 text-white lg:flex">
        <div>
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-white/15 text-base font-semibold">P</div>
          <p className="mt-10 text-sm text-white/80">{companyName}</p>
          <h1 className="mt-2 max-w-sm text-4xl font-semibold tracking-tight">Leave, without the chase.</h1>
          <p className="mt-4 max-w-sm text-sm leading-6 text-white/80">
            PeopleHub keeps balances, requests, and the calendar in one place for a small team.
          </p>
        </div>
        <ul className="space-y-2 text-sm text-white/85">
          <li>See what leave you have left</li>
          <li>Submit a request in a few fields</li>
          <li>Administrators review from one queue</li>
        </ul>
      </section>
      <section className="flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-md">
          <div className="mb-8 lg:hidden">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-brand text-sm font-semibold text-white">P</div>
            <h1 className="mt-4 text-2xl font-semibold">PeopleHub</h1>
          </div>
          <h2 className="text-xl font-semibold tracking-tight">Sign in</h2>
          <p className="mt-1 text-sm text-muted">Use the work email an administrator created for you.</p>
          <div className="mt-6 rounded-xl border border-line bg-white p-6">
            <LoginForm next={next} />
          </div>
          <p className="mt-4 text-xs text-muted">There is no public registration. Ask an administrator for an account.</p>
        </div>
      </section>
    </main>
  );
}
