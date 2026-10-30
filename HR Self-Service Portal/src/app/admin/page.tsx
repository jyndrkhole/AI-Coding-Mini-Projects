import Link from "next/link";
import { addDaysIso, dateOnly, formatDateRange, formatDays, isoFromDateOnly, startOfZonedDay, todayIso } from "@/lib/dates";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { requireAdmin } from "@/server/auth/guard";
import { prisma } from "@/server/db";
import { getOrganization } from "@/server/services/organization";

export const metadata = { title: "Admin Dashboard" };

export default async function AdminDashboardPage() {
  await requireAdmin();
  const organization = await getOrganization();
  const today = todayIso(organization.timezone);
  const monthStart = startOfZonedDay(`${today.slice(0, 8)}01`, organization.timezone);
  const nextMonth = startOfZonedDay(addDaysIso(`${today.slice(0, 8)}01`, 32).slice(0, 8) + "01", organization.timezone);

  const [activeEmployees, pendingRequests, pendingCount, onLeaveDays, upcoming, submittedThisMonth, recentAudit, employees] =
    await Promise.all([
      prisma.employee.count({ where: { employmentStatus: "ACTIVE" } }),
      prisma.leaveRequest.findMany({
        where: { status: "PENDING" },
        include: { employee: true, leaveType: true },
        orderBy: { submittedAt: "asc" },
        take: 8,
      }),
      prisma.leaveRequest.count({ where: { status: "PENDING" } }),
      prisma.leaveRequestDay.findMany({
        where: { leaveDate: dateOnly(today), leaveRequest: { status: "APPROVED" } },
        select: { leaveRequest: { select: { employeeId: true } } },
      }),
      prisma.leaveRequest.count({
        where: { status: "APPROVED", endDate: { gte: dateOnly(today) } },
      }),
      prisma.leaveRequest.count({
        where: { submittedAt: { gte: monthStart, lt: nextMonth } },
      }),
      prisma.auditLog.findMany({ orderBy: { createdAt: "desc" }, take: 6, include: { actor: true } }),
      prisma.employee.findMany({
        include: { user: true },
        orderBy: { fullName: "asc" },
        take: 8,
      }),
    ]);

  const onLeaveToday = new Set(onLeaveDays.map((day) => day.leaveRequest.employeeId)).size;
  const cards = [
    ["Active employees", activeEmployees],
    ["On leave today", onLeaveToday],
    ["Upcoming approved", upcoming],
    ["Pending requests", pendingCount],
    ["Submitted this month", submittedThisMonth],
  ] as const;

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">Admin Dashboard</h1>
      <p className="mt-1 text-sm text-muted">Organization leave at a glance.</p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {cards.map(([label, value]) => (
          <article key={label} className="rounded-xl border border-line bg-white p-4">
            <p className="text-sm text-muted">{label}</p>
            <p className="mt-2 text-2xl font-semibold">{value}</p>
          </article>
        ))}
      </div>

      <section className="mt-8">
        <h2 className="mb-3 text-sm font-medium text-muted">Pending requests</h2>
        {pendingRequests.length === 0 ? (
          <EmptyState title="No pending requests" body="New leave requests will wait here for review." />
        ) : (
          <div className="overflow-x-auto rounded-xl border border-line bg-white">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b border-line text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Employee</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Dates</th>
                  <th className="px-4 py-3 font-medium">Days</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium"> </th>
                </tr>
              </thead>
              <tbody>
                {pendingRequests.map((request) => (
                  <tr key={request.id} className="border-b border-line last:border-0">
                    <td className="px-4 py-3">{request.employee.fullName}</td>
                    <td className="px-4 py-3">{request.leaveType.name}</td>
                    <td className="px-4 py-3">{formatDateRange(isoFromDateOnly(request.startDate), isoFromDateOnly(request.endDate))}</td>
                    <td className="px-4 py-3">{formatDays(request.requestedDays.toNumber())}</td>
                    <td className="px-4 py-3"><StatusBadge status={request.status} /></td>
                    <td className="px-4 py-3 text-right">
                      <Link href="/admin/leave" className="font-medium text-brand">Review</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-sm font-medium text-muted">Employees</h2>
          <ul className="divide-y divide-line rounded-xl border border-line bg-white">
            {employees.map((employee) => (
              <li key={employee.id} className="px-4 py-3 text-sm">
                <p className="font-medium">{employee.fullName}</p>
                <p className="text-muted">
                  {employee.employeeCode} · {employee.department} · {employee.user.role === "ADMINISTRATOR" ? "Administrator" : "Employee"}
                </p>
              </li>
            ))}
          </ul>
        </section>
        <section>
          <h2 className="mb-3 text-sm font-medium text-muted">Recent activity</h2>
          {recentAudit.length === 0 ? (
            <EmptyState title="No activity yet" body="Approvals, employee changes, and balance adjustments will be listed here." />
          ) : (
            <ul className="divide-y divide-line rounded-xl border border-line bg-white">
              {recentAudit.map((entry) => (
                <li key={entry.id} className="px-4 py-3 text-sm">
                  <p className="font-medium">{entry.action}</p>
                  <p className="text-muted">{entry.actor?.email ?? "System"}</p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
