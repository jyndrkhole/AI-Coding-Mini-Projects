import { LeaveMonth } from "@/components/calendar/leave-month";
import { PageHeader } from "@/components/layout/page-header";
import { todayIso } from "@/lib/dates";
import { requireUser } from "@/server/auth/guard";
import { getOrganization } from "@/server/services/organization";

export const metadata = { title: "Leave Calendar" };

export default async function EmployeeCalendarPage({
  searchParams,
}: {
  searchParams: Promise<{ year?: string; month?: string }>;
}) {
  const session = await requireUser();
  const organization = await getOrganization();
  const params = await searchParams;
  const today = todayIso(organization.timezone);
  const year = Number(params.year) || Number(today.slice(0, 4));
  const month = Number(params.month) || Number(today.slice(5, 7));

  return (
    <div>
      <PageHeader title="Leave Calendar" description="Your leave and the rest of the organization, without private reasons." />
      <LeaveMonth
        year={year}
        month={month}
        scope="employee"
        viewerEmployeeId={session.user.employee?.id ?? null}
        basePath="/calendar"
      />
    </div>
  );
}
