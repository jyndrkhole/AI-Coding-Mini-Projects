import { AppShell } from "@/components/layout/app-shell";
import { requireUser } from "@/server/auth/guard";
import { getOrganization } from "@/server/services/organization";

export default async function EmployeeLayout({ children }: { children: React.ReactNode }) {
  const [session, organization] = await Promise.all([requireUser(), getOrganization()]);
  return (
    <AppShell
      portal="employee"
      companyName={organization.companyName}
      userName={session.user.employee?.fullName ?? session.user.email}
      email={session.user.email}
      role={session.user.role}
    >
      {children}
    </AppShell>
  );
}
