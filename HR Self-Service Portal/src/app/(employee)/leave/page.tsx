import { Notice } from "@/components/feedback/notice";
import { PageHeader } from "@/components/layout/page-header";
import { ButtonLink } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatDateRange, formatDays } from "@/lib/dates";
import { cancelLeaveAction } from "@/server/actions/portal";
import { requireUser } from "@/server/auth/guard";
import { listLeaveRequests } from "@/server/services/leave";

export const metadata = { title: "My Leaves" };

export default async function MyLeavesPage({
  searchParams,
}: {
  searchParams: Promise<{ notice?: string; error?: string; days?: string }>;
}) {
  const session = await requireUser();
  const employee = session.user.employee;
  const params = await searchParams;
  if (!employee) {
    return <EmptyState title="Profile missing" body="An administrator needs to finish setting up your employee record." />;
  }
  const requests = await listLeaveRequests({ employeeId: employee.id });

  return (
    <div>
      <PageHeader
        title="My Leaves"
        description="Pending leave is not treated as used until it is approved."
        action={<ButtonLink href="/leave/new">Apply for Leave</ButtonLink>}
      />
      <Notice notice={params.notice} error={params.error} />
      {params.notice === "submitted" && params.days ? (
        <p className="-mt-2 mb-4 text-sm text-muted">{params.days} working days were saved with this request.</p>
      ) : null}
      {requests.length === 0 ? (
        <EmptyState title="No leave requests" body="Requests you submit will stay here, including ones that are cancelled or rejected." actionHref="/leave/new" actionLabel="Apply for Leave" />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-line bg-white">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="border-b border-line text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Dates</th>
                <th className="px-4 py-3 font-medium">Days</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium"> </th>
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <tr key={request.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">
                    <p className="font-medium">{request.leaveTypeName}</p>
                    {request.reason ? <p className="text-muted">{request.reason}</p> : null}
                    {request.reviewComment ? <p className="text-muted">Note: {request.reviewComment}</p> : null}
                  </td>
                  <td className="px-4 py-3">{formatDateRange(request.startIso, request.endIso)}</td>
                  <td className="px-4 py-3">{formatDays(request.requestedDays)}</td>
                  <td className="px-4 py-3"><StatusBadge status={request.status} /></td>
                  <td className="px-4 py-3 text-right">
                    {request.canCancel ? (
                      <form action={cancelLeaveAction}>
                        <input type="hidden" name="requestId" value={request.id} />
                        <button type="submit" className="text-sm font-medium text-danger">
                          Cancel
                        </button>
                      </form>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
