import { AppShell } from "@/components/layout/app-shell";
import { requireAdmin } from "@/server/auth/guard";
import { getOrganization } from "@/server/services/organization";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const [session, organization] = await Promise.all([requireAdmin(), getOrganization()]);
  return (
    <AppShell
      portal="admin"
      companyName={organization.companyName}
      userName={session.user.employee?.fullName ?? session.user.email}
      email={session.user.email}
      role={session.user.role}
    >
      {children}
    </AppShell>
  );
}
