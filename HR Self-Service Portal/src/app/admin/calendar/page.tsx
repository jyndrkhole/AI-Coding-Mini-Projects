import { LeaveMonth } from "@/components/calendar/leave-month";
import { PageHeader } from "@/components/layout/page-header";
import { todayIso } from "@/lib/dates";
import { requireAdmin } from "@/server/auth/guard";
import { getOrganization } from "@/server/services/organization";

export const metadata = { title: "Leave Calendar" };

export default async function AdminCalendarPage({
  searchParams,
}: {
  searchParams: Promise<{ year?: string; month?: string }>;
}) {
  const session = await requireAdmin();
  const organization = await getOrganization();
  const params = await searchParams;
  const today = todayIso(organization.timezone);
  const year = Number(params.year) || Number(today.slice(0, 4));
  const month = Number(params.month) || Number(today.slice(5, 7));

  return (
    <div>
      <PageHeader title="Leave Calendar" description="Approved and pending leave across the organization." />
      <LeaveMonth
        year={year}
        month={month}
        scope="admin"
        viewerEmployeeId={session.user.employee?.id ?? null}
        basePath="/admin/calendar"
      />
    </div>
  );
}
