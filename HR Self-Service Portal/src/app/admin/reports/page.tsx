import Link from "next/link";
import { PageHeader } from "@/components/layout/page-header";
import { Button, ButtonLink } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatDateRange, formatDays, monthBoundsIso, todayIso } from "@/lib/dates";
import { requireAdmin } from "@/server/auth/guard";
import { prisma } from "@/server/db";
import { getOrganization } from "@/server/services/organization";
import { listLeaveRequests, resolveReportScope } from "@/server/services/leave";

export const metadata = { title: "Reports" };

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<{ employee?: string; from?: string; to?: string }>;
}) {
  await requireAdmin();
  const params = await searchParams;
  const organization = await getOrganization();
  const month = monthBoundsIso(todayIso(organization.timezone));
  const scope = await resolveReportScope(params);
  const [requests, employees] = await Promise.all([
    listLeaveRequests(scope),
    prisma.employee.findMany({
      orderBy: { fullName: "asc" },
      select: { id: true, fullName: true, employeeCode: true },
    }),
  ]);
  const byStatus = new Map<string, number>();
  for (const request of requests) {
    byStatus.set(request.status, (byStatus.get(request.status) ?? 0) + 1);
  }

  const exportQuery = new URLSearchParams({
    from: scope.fromIso ?? month.fromIso,
    to: scope.toIso ?? month.toIso,
  });
  if (scope.employeeId) exportQuery.set("employee", scope.employeeId);
  const changed =
    Boolean(scope.employeeId) || scope.fromIso !== month.fromIso || scope.toIso !== month.toIso;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description="Dates open on this month. Apply, then use Export for the leave shown here."
      />
      <form method="get" className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-white p-4">
        <div className="w-full sm:w-44">
          <Field label="From">
            <Input name="from" type="date" defaultValue={scope.fromIso ?? ""} />
          </Field>
        </div>
        <div className="w-full sm:w-44">
          <Field label="To">
            <Input name="to" type="date" defaultValue={scope.toIso ?? ""} />
          </Field>
        </div>
        <div className="w-full sm:w-64">
          <Field label="Employee">
            <Select name="employee" defaultValue={scope.employeeId ?? ""}>
              <option value="">All employees</option>
              {employees.map((employee) => (
                <option key={employee.id} value={employee.id}>
                  {employee.fullName} ({employee.employeeCode})
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <Button type="submit" variant="secondary">
          Apply
        </Button>
        <ButtonLink href={`/admin/reports/export?${exportQuery}`}>Export</ButtonLink>
        {changed ? (
          <Link href="/admin/reports" className="inline-flex h-10 items-center px-2 text-sm font-medium text-muted">
            This month
          </Link>
        ) : null}
      </form>
      <div className="grid gap-3 sm:grid-cols-4">
        {["PENDING", "APPROVED", "REJECTED", "CANCELLED"].map((status) => (
          <article key={status} className="rounded-xl border border-line bg-white p-4">
            <p className="text-sm text-muted">{status[0] + status.slice(1).toLowerCase()}</p>
            <p className="mt-1 text-2xl font-semibold">{byStatus.get(status) ?? 0}</p>
          </article>
        ))}
      </div>
      <div className="overflow-x-auto rounded-xl border border-line bg-white">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Employee</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Dates</th>
              <th className="px-4 py-3 font-medium">Days</th>
              <th className="px-4 py-3 font-medium">US team</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {requests.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-muted">
                  No leave matches these filters.
                </td>
              </tr>
            ) : (
              requests.map((request) => (
                <tr key={request.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">{request.employeeName}</td>
                  <td className="px-4 py-3">{request.leaveTypeName}</td>
                  <td className="px-4 py-3">{formatDateRange(request.startIso, request.endIso)}</td>
                  <td className="px-4 py-3">{formatDays(request.requestedDays)}</td>
                  <td className="px-4 py-3">{request.informUsTeam ? "Informed" : "Not informed"}</td>
                  <td className="px-4 py-3"><StatusBadge status={request.status} /></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
