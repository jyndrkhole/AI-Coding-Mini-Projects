import { LeaveForm } from "@/components/leave/leave-form";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/layout/page-header";
import { isoFromDateOnly } from "@/lib/dates";
import { requireUser } from "@/server/auth/guard";
import { prisma } from "@/server/db";
import { getBalanceCards } from "@/server/services/leave";
import { getOrganization } from "@/server/services/organization";

export const metadata = { title: "Apply for Leave" };

export default async function ApplyForLeavePage() {
  const session = await requireUser();
  const employee = session.user.employee;
  if (!employee) {
    return <EmptyState title="Profile missing" body="An administrator needs to finish setting up your employee record." />;
  }

  const [organization, types, cards, holidays] = await Promise.all([
    getOrganization(),
    prisma.leaveType.findMany({ where: { isActive: true }, orderBy: { sortOrder: "asc" } }),
    getBalanceCards(employee.id),
    prisma.holiday.findMany({ where: { isActive: true } }),
  ]);

  return (
    <div>
      <PageHeader title="Apply for Leave" description="The number of working days is calculated again when you submit." />
      {types.length === 0 ? (
        <EmptyState title="No leave types yet" body="An administrator needs to configure leave types before you can apply." />
      ) : (
        <LeaveForm
          weekendDays={organization.weekendDays}
          holidayIsos={holidays.map((holiday) => isoFromDateOnly(holiday.holidayDate))}
          leaveTypes={types.map((type) => ({
            id: type.id,
            name: type.name,
            allowsHalfDay: type.allowsHalfDay,
            requiresReason: type.requiresReason,
            available: cards.find((card) => card.leaveTypeId === type.id)?.available ?? null,
          }))}
        />
      )}
    </div>
  );
}
