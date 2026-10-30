import { notFound } from "next/navigation";
import { Notice } from "@/components/feedback/notice";
import { PageHeader } from "@/components/layout/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatDateRange, formatDays, formatDisplayDate } from "@/lib/dates";
import { setEmploymentStatusAction } from "@/server/actions/portal";
import { requireAdmin } from "@/server/auth/guard";
import { prisma } from "@/server/db";
import { getBalanceCards, listLeaveRequests } from "@/server/services/leave";

export const metadata = { title: "Employee" };

export default async function EmployeeDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ notice?: string; error?: string }>;
}) {
  await requireAdmin();
  const { id } = await params;
  const query = await searchParams;
  const employee = await prisma.employee.findUnique({ where: { id }, include: { user: true } });
  if (!employee) notFound();
  const [cards, requests] = await Promise.all([
    getBalanceCards(employee.id),
    listLeaveRequests({ employeeId: employee.id }),
  ]);

  return (
    <div className="space-y-8">
      <PageHeader title={employee.fullName} description={`${employee.employeeCode} · ${employee.user.email}`} />
      <Notice notice={query.notice} error={query.error} />
      <dl className="grid gap-3 rounded-xl border border-line bg-white p-4 text-sm sm:grid-cols-3">
        <div><dt className="text-muted">Department</dt><dd>{employee.department}</dd></div>
        <div><dt className="text-muted">Designation</dt><dd>{employee.designation}</dd></div>
        <div><dt className="text-muted">Joined</dt><dd>{formatDisplayDate(employee.joiningDate.toISOString().slice(0, 10))}</dd></div>
      </dl>
      <form action={setEmploymentStatusAction}>
        <input type="hidden" name="employeeId" value={employee.id} />
        <input type="hidden" name="status" value={employee.employmentStatus === "ACTIVE" ? "INACTIVE" : "ACTIVE"} />
        <button type="submit" className="text-sm font-medium text-brand">
          {employee.employmentStatus === "ACTIVE" ? "Deactivate employee" : "Activate employee"}
        </button>
      </form>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Balances</h2>
        <ul className="grid gap-3 sm:grid-cols-2">
          {cards.map((card) => (
            <li key={card.leaveTypeId} className="rounded-xl border border-line bg-white p-4 text-sm">
              <p className="font-medium">{card.name}</p>
              <p className="mt-1 text-muted">
                {card.available == null ? "Not tracked" : `${formatDays(card.available)} available`} · {formatDays(card.pending)} pending
              </p>
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Leave history</h2>
        <ul className="divide-y divide-line rounded-xl border border-line bg-white">
          {requests.map((request) => (
            <li key={request.id} className="flex items-center justify-between px-4 py-3 text-sm">
              <span>
                {request.leaveTypeName} · {formatDateRange(request.startIso, request.endIso)}
              </span>
              <StatusBadge status={request.status} />
            </li>
          ))}
          {requests.length === 0 ? <li className="px-4 py-6 text-sm text-muted">No leave requests.</li> : null}
        </ul>
      </section>
    </div>
  );
}
