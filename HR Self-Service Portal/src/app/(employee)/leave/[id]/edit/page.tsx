import { notFound } from "next/navigation";
import { LeaveForm } from "@/components/leave/leave-form";
import { PageHeader } from "@/components/layout/page-header";
import { ButtonLink } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { isoFromDateOnly, roundDay } from "@/lib/dates";
import { requireUser } from "@/server/auth/guard";
import { prisma } from "@/server/db";
import { getBalanceCards } from "@/server/services/leave";
import { getOrganization } from "@/server/services/organization";

export const metadata = { title: "Edit leave" };

export default async function EditLeavePage({ params }: { params: Promise<{ id: string }> }) {
  const session = await requireUser();
  const employee = session.user.employee;
  if (!employee) {
    return <EmptyState title="Profile missing" body="An administrator needs to finish setting up your employee record." />;
  }

  const { id } = await params;
  const request = await prisma.leaveRequest.findUnique({ where: { id } });
  if (!request || request.employeeId !== employee.id) notFound();
  if (request.status !== "PENDING") {
    return (
      <EmptyState
        title="This request can no longer be edited"
        body="Only a pending request can be changed. Approved leave stays as it was reviewed."
        actionHref="/leave"
        actionLabel="Back to My Leaves"
      />
    );
  }

  const [organization, types, cards, holidays] = await Promise.all([
    getOrganization(),
    prisma.leaveType.findMany({
      where: { OR: [{ isActive: true }, { id: request.leaveTypeId }] },
      orderBy: { sortOrder: "asc" },
    }),
    getBalanceCards(employee.id),
    prisma.holiday.findMany({ where: { isActive: true } }),
  ]);
  const requestedDays = roundDay(request.requestedDays.toNumber());

  return (
    <div>
      <PageHeader
        title="Edit leave"
        description="Saving checks the balance and dates again. Approved leave cannot be edited."
        action={<ButtonLink href="/leave" variant="secondary">Back to My Leaves</ButtonLink>}
      />
      <LeaveForm
        weekendDays={organization.weekendDays}
        holidayIsos={holidays.map((holiday) => isoFromDateOnly(holiday.holidayDate))}
        draft={{
          requestId: request.id,
          leaveTypeId: request.leaveTypeId,
          startDate: isoFromDateOnly(request.startDate),
          endDate: isoFromDateOnly(request.endDate),
          startPortion: request.startPortion,
          endPortion: request.endPortion,
          reason: request.reason,
          informUsTeam: request.informUsTeam,
        }}
        leaveTypes={types.map((type) => {
          const card = cards.find((item) => item.leaveTypeId === type.id);
          const available = card?.available ?? null;
          return {
            id: type.id,
            name: type.name,
            allowsHalfDay: type.allowsHalfDay,
            requiresReason: type.requiresReason,
            available:
              available == null
                ? null
                : roundDay(available - (card?.pending ?? 0) + (type.id === request.leaveTypeId ? requestedDays : 0)),
          };
        })}
      />
    </div>
  );
}
