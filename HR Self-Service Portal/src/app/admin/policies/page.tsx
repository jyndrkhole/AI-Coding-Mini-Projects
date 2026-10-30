import { HolidayForm, LeaveTypeForm } from "@/components/admin/admin-forms";
import { Notice } from "@/components/feedback/notice";
import { PageHeader } from "@/components/layout/page-header";
import { formatDisplayDate } from "@/lib/dates";
import { requireAdmin } from "@/server/auth/guard";
import { prisma } from "@/server/db";
import { getOrganization } from "@/server/services/organization";

export const metadata = { title: "Leave Types & Policies" };

export default async function PoliciesPage({
  searchParams,
}: {
  searchParams: Promise<{ notice?: string; error?: string }>;
}) {
  await requireAdmin();
  const params = await searchParams;
  const [organization, leaveTypes, holidays] = await Promise.all([
    getOrganization(),
    prisma.leaveType.findMany({ orderBy: { sortOrder: "asc" } }),
    prisma.holiday.findMany({ where: { isActive: true }, orderBy: { holidayDate: "asc" } }),
  ]);
  const weekend = organization.weekendDays.map((day) => ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][day]).join(", ");

  return (
    <div className="space-y-8">
      <PageHeader
        title="Leave Types & Policies"
        description={`Leave year starts ${organization.leaveYearStartDay}/${organization.leaveYearStartMonth}. Weekend: ${weekend || "none"}. Timezone: ${organization.timezone}.`}
      />
      <Notice notice={params.notice} error={params.error} />
      <ul className="divide-y divide-line rounded-xl border border-line bg-white">
        {leaveTypes.map((type) => (
          <li key={type.id} className="px-4 py-3 text-sm">
            <p className="font-medium">{type.name}</p>
            <p className="text-muted">
              {type.defaultAnnualEntitlement.toString()} days · {type.tracksBalance ? "Balance tracked" : "Balance not tracked"} ·{" "}
              {type.isActive ? "Active" : "Inactive"}
            </p>
          </li>
        ))}
        {leaveTypes.length === 0 ? <li className="px-4 py-6 text-sm text-muted">No leave types yet.</li> : null}
      </ul>
      <section>
        <h2 className="mb-3 text-lg font-semibold">New leave type</h2>
        <LeaveTypeForm />
      </section>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Holidays</h2>
        <ul className="divide-y divide-line rounded-xl border border-line bg-white">
          {holidays.map((holiday) => (
            <li key={holiday.id} className="px-4 py-3 text-sm">
              {holiday.name} · {formatDisplayDate(holiday.holidayDate.toISOString().slice(0, 10))}
            </li>
          ))}
          {holidays.length === 0 ? <li className="px-4 py-6 text-sm text-muted">No holidays configured.</li> : null}
        </ul>
        <HolidayForm />
      </section>
    </div>
  );
}
