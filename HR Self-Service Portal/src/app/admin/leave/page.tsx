import { Notice } from "@/components/feedback/notice";
import { PageHeader } from "@/components/layout/page-header";
import { ReviewForm } from "@/components/leave/review-form";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatDateRange, formatDays } from "@/lib/dates";
import { requireAdmin } from "@/server/auth/guard";
import { listLeaveRequests } from "@/server/services/leave";

export const metadata = { title: "Leave Management" };

export default async function AdminLeavePage({
  searchParams,
}: {
  searchParams: Promise<{ notice?: string; error?: string }>;
}) {
  const session = await requireAdmin();
  const params = await searchParams;
  const requests = await listLeaveRequests({});

  return (
    <div>
      <PageHeader title="Leave Management" description="Review pending requests. You cannot approve your own leave." />
      <Notice notice={params.notice} error={params.error} />
      {requests.length === 0 ? (
        <EmptyState title="No leave requests" body="Employee submissions will appear in this list." />
      ) : (
        <div className="space-y-3">
          {requests.map((request) => (
            <article key={request.id} className="rounded-xl border border-line bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium">
                    {request.employeeName}{" "}
                    <span className="font-normal text-muted">{request.employeeCode}</span>
                  </p>
                  <p className="text-sm text-muted">
                    {request.leaveTypeName} · {formatDateRange(request.startIso, request.endIso)} · {formatDays(request.requestedDays)} days
                  </p>
                  {request.reason ? <p className="mt-2 text-sm">{request.reason}</p> : null}
                </div>
                <StatusBadge status={request.status} />
              </div>
              {request.status === "PENDING" && request.employeeId !== session.user.employee?.id ? (
                <ReviewForm requestId={request.id} />
              ) : null}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
