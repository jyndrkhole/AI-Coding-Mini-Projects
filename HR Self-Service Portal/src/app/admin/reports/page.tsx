import Link from "next/link";
import { PageHeader } from "@/components/layout/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatDateRange, formatDays } from "@/lib/dates";
import { requireAdmin } from "@/server/auth/guard";
import { listLeaveRequests } from "@/server/services/leave";

export const metadata = { title: "Reports" };

export default async function ReportsPage() {
  await requireAdmin();
  const requests = await listLeaveRequests({});
  const byStatus = new Map<string, number>();
  for (const request of requests) {
    byStatus.set(request.status, (byStatus.get(request.status) ?? 0) + 1);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description="Request counts by status, with a CSV export of the same records."
        action={
          <Link href="/admin/reports/export" className="inline-flex h-10 items-center rounded-lg border border-line bg-white px-4 text-sm font-medium">
            Export CSV
          </Link>
        }
      />
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
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {requests.map((request) => (
              <tr key={request.id} className="border-b border-line last:border-0">
                <td className="px-4 py-3">{request.employeeName}</td>
                <td className="px-4 py-3">{request.leaveTypeName}</td>
                <td className="px-4 py-3">{formatDateRange(request.startIso, request.endIso)}</td>
                <td className="px-4 py-3">{formatDays(request.requestedDays)}</td>
                <td className="px-4 py-3"><StatusBadge status={request.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
