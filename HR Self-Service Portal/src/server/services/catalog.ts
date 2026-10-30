import { Prisma } from "@prisma/client";
import { dateOnly, leaveYearStartIso, roundDay, todayIso } from "@/lib/dates";
import { prisma } from "@/server/db";
import type { ServiceResult } from "@/server/services/leave";
import { getOrganization } from "@/server/services/organization";

function fail(error: string): ServiceResult<never> {
  return { ok: false, error };
}

export async function createLeaveType(input: {
  actorUserId: string;
  name: string;
  description: string;
  isPaid: boolean;
  tracksBalance: boolean;
  defaultAnnualEntitlement: number;
  allowsHalfDay: boolean;
  allowsNegativeBalance: boolean;
  carryForwardEligible: boolean;
  maxCarryForwardDays: number | null;
  requiresReason: boolean;
}): Promise<ServiceResult<{ id: string }>> {
  const name = input.name.trim();
  if (!name) return fail("Enter a leave type name.");
  if (input.defaultAnnualEntitlement < 0 || roundDay(input.defaultAnnualEntitlement) * 2 % 1 !== 0) {
    return fail("Entitlement must be zero or a multiple of half a day.");
  }

  const organization = await getOrganization();
  const yearStart = dateOnly(
    leaveYearStartIso(todayIso(organization.timezone), organization.leaveYearStartMonth, organization.leaveYearStartDay),
  );

  try {
    const created = await prisma.$transaction(async (tx) => {
      const count = await tx.leaveType.count();
      const leaveType = await tx.leaveType.create({
        data: {
          name,
          description: input.description.trim(),
          isPaid: input.isPaid,
          tracksBalance: input.tracksBalance,
          defaultAnnualEntitlement: roundDay(input.defaultAnnualEntitlement).toFixed(1),
          allowsHalfDay: input.allowsHalfDay,
          allowsNegativeBalance: input.allowsNegativeBalance,
          carryForwardEligible: input.carryForwardEligible,
          maxCarryForwardDays:
            input.carryForwardEligible && input.maxCarryForwardDays != null
              ? roundDay(input.maxCarryForwardDays).toFixed(1)
              : null,
          requiresReason: input.requiresReason,
          sortOrder: count,
        },
      });
      const employees = await tx.employee.findMany({
        where: { employmentStatus: "ACTIVE" },
        select: { id: true },
      });
      if (employees.length > 0) {
        await tx.leaveEntitlement.createMany({
          data: employees.map((employee) => ({
            employeeId: employee.id,
            leaveTypeId: leaveType.id,
            yearStart,
            entitledDays: leaveType.defaultAnnualEntitlement,
          })),
        });
      }
      await tx.auditLog.create({
        data: {
          actorUserId: input.actorUserId,
          action: "leaveType.created",
          entityType: "LeaveType",
          entityId: leaveType.id,
          metadata: { name },
        },
      });
      return leaveType;
    });
    return { ok: true, value: { id: created.id } };
  } catch (error) {
    if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002") {
      return fail("A leave type with this name already exists.");
    }
    throw error;
  }
}

export async function adjustBalance(input: {
  actorUserId: string;
  employeeId: string;
  leaveTypeId: string;
  adjustmentDays: number;
  reason: string;
}): Promise<ServiceResult<{ id: string }>> {
  const reason = input.reason.trim();
  const amount = roundDay(input.adjustmentDays);
  if (!reason) return fail("Enter a reason for the adjustment.");
  if (amount === 0) return fail("Enter an adjustment other than zero.");

  const organization = await getOrganization();
  const yearStart = dateOnly(
    leaveYearStartIso(todayIso(organization.timezone), organization.leaveYearStartMonth, organization.leaveYearStartDay),
  );

  const [employee, leaveType] = await Promise.all([
    prisma.employee.findUnique({ where: { id: input.employeeId } }),
    prisma.leaveType.findUnique({ where: { id: input.leaveTypeId } }),
  ]);
  if (!employee || !leaveType) return fail("Choose an employee and a leave type.");
  if (!leaveType.tracksBalance) return fail("This leave type does not track a balance.");

  const adjustment = await prisma.$transaction(async (tx) => {
    const created = await tx.leaveBalanceAdjustment.create({
      data: {
        employeeId: employee.id,
        leaveTypeId: leaveType.id,
        yearStart,
        adjustmentDays: amount.toFixed(1),
        reason,
        adjustedByUserId: input.actorUserId,
      },
    });
    await tx.auditLog.create({
      data: {
        actorUserId: input.actorUserId,
        action: "balance.adjusted",
        entityType: "LeaveBalanceAdjustment",
        entityId: created.id,
        metadata: { employeeId: employee.id, leaveType: leaveType.name, adjustmentDays: amount },
      },
    });
    return created;
  });

  return { ok: true, value: { id: adjustment.id } };
}

export async function createHoliday(input: {
  actorUserId: string;
  name: string;
  holidayDate: string;
}): Promise<ServiceResult<{ id: string }>> {
  const name = input.name.trim();
  if (!name || !/^\d{4}-\d{2}-\d{2}$/.test(input.holidayDate)) {
    return fail("Enter a holiday name and date.");
  }
  try {
    const holiday = await prisma.holiday.create({
      data: { name, holidayDate: dateOnly(input.holidayDate) },
    });
    await prisma.auditLog.create({
      data: {
        actorUserId: input.actorUserId,
        action: "holiday.created",
        entityType: "Holiday",
        entityId: holiday.id,
        metadata: { name, holidayDate: input.holidayDate },
      },
    });
    return { ok: true, value: { id: holiday.id } };
  } catch (error) {
    if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002") {
      return fail("A holiday is already set on that date.");
    }
    throw error;
  }
}
