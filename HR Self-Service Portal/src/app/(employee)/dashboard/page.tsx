import { ButtonLink } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatDateRange, formatDays, formatLongDate, greetingFor, todayIso } from "@/lib/dates";
import { requireUser } from "@/server/auth/guard";
import { getBalanceCards, listLeaveRequests } from "@/server/services/leave";
import { getOrganization } from "@/server/services/organization";

export const metadata = { title: "My Dashboard" };

export default async function EmployeeDashboardPage() {
  const session = await requireUser();
  const employee = session.user.employee;
  if (!employee) {
    return <EmptyState title="Profile missing" body="An administrator needs to finish setting up your employee record." />;
  }

  const organization = await getOrganization();
  const today = todayIso(organization.timezone);
  const [cards, requests] = await Promise.all([
    getBalanceCards(employee.id),
    listLeaveRequests({ employeeId: employee.id }),
  ]);
  const upcoming = requests.filter((request) => request.status === "APPROVED" && request.endIso >= today).slice(0, 5);
  const recent = requests.slice(0, 5);
  const firstName = employee.fullName.split(" ")[0];

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm text-muted">{formatLongDate(new Date(), organization.timezone)}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            {greetingFor(organization.timezone)}, {firstName}
          </h1>
        </div>
        <ButtonLink href="/leave/new">Apply for Leave</ButtonLink>
      </div>

      <section>
        <h2 className="mb-3 text-sm font-medium text-muted">Leave balances</h2>
        {cards.length === 0 ? (
          <EmptyState
            title="No leave types yet"
            body="Balances appear after an administrator configures leave types and entitlements."
          />
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {cards.map((card) => {
                const allocated = card.entitlement + card.adjustments;
                const usedShare = allocated > 0 ? Math.min(100, (card.approvedTaken / allocated) * 100) : 0;
                return (
                  <article key={card.leaveTypeId} className="rounded-xl border border-line bg-white p-4">
                    <h3 className="text-sm font-medium text-ink">{card.name}</h3>
                    <p className="mt-3 text-3xl font-semibold tracking-tight">
                      {card.available == null ? "—" : formatDays(card.available)}
                    </p>
                    <p className="text-sm text-muted">{card.available == null ? "Balance not tracked" : "available"}</p>
                    <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <dt className="text-muted">Entitlement</dt>
                        <dd>{formatDays(card.entitlement)}</dd>
                      </div>
                      <div>
                        <dt className="text-muted">Used</dt>
                        <dd>{formatDays(card.approvedTaken)}</dd>
                      </div>
                      <div>
                        <dt className="text-muted">Upcoming</dt>
                        <dd>{formatDays(card.approvedUpcoming)}</dd>
                      </div>
                      <div>
                        <dt className="text-muted">Pending</dt>
                        <dd>{formatDays(card.pending)}</dd>
                      </div>
                    </dl>
                    {card.tracksBalance ? (
                      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-canvas">
                        <div className="h-full rounded-full bg-brand" style={{ width: `${usedShare}%` }} />
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
            <p className="mt-3 text-xs text-muted">Pending requests are shown separately and are not counted as used leave.</p>
          </>
        )}
      </section>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-sm font-medium text-muted">Upcoming leave</h2>
          {upcoming.length === 0 ? (
            <EmptyState title="Nothing upcoming" body="Approved leave that is still ahead will show here." />
          ) : (
            <ul className="divide-y divide-line rounded-xl border border-line bg-white">
              {upcoming.map((request) => (
                <li key={request.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                  <div>
                    <p className="font-medium">{request.leaveTypeName}</p>
                    <p className="text-muted">{formatDateRange(request.startIso, request.endIso)}</p>
                  </div>
                  <div className="text-right">
                    <StatusBadge status={request.status} />
                    <p className="mt-1 text-muted">{formatDays(request.requestedDays)} days</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium text-muted">Recent requests</h2>
            <ButtonLink href="/leave" variant="ghost" size="sm">
              View history
            </ButtonLink>
          </div>
          {recent.length === 0 ? (
            <EmptyState
              title="No requests yet"
              body="When you apply for leave, the request and its status will show here."
              actionHref="/leave/new"
              actionLabel="Apply for Leave"
            />
          ) : (
            <ul className="divide-y divide-line rounded-xl border border-line bg-white">
              {recent.map((request) => (
                <li key={request.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                  <div>
                    <p className="font-medium">{request.leaveTypeName}</p>
                    <p className="text-muted">{formatDateRange(request.startIso, request.endIso)}</p>
                  </div>
                  <StatusBadge status={request.status} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
