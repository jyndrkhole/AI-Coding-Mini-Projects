import { Prisma, type DayPortion, type LeaveRequestStatus, type PrismaClient } from "@prisma/client";
import { calculateBalance, requestExceedsBalance } from "@/lib/balance";
import { employeeCanCancelRequest } from "@/lib/cancellation";
import {
  dateOnly,
  isoFromDateOnly,
  isIsoDate,
  leaveYearStartIso,
  roundDay,
  todayIso,
} from "@/lib/dates";
import { countLeaveDays } from "@/lib/leave-days";
import { prisma } from "@/server/db";
import { getOrganization } from "@/server/services/organization";

type Db = PrismaClient | Prisma.TransactionClient;

export type ServiceResult<T> = { ok: true; value: T } | { ok: false; error: string };

function ok<T>(value: T): ServiceResult<T> {
  return { ok: true, value };
}

function fail(error: string): ServiceResult<never> {
  return { ok: false, error };
}

function days(value: Prisma.Decimal | number | null | undefined) {
  if (value == null) return 0;
  const numeric = typeof value === "number" ? value : value.toNumber();
  return roundDay(numeric);
}

export type BalanceCard = {
  leaveTypeId: string;
  name: string;
  tracksBalance: boolean;
  entitlement: number;
  adjustments: number;
  approvedTaken: number;
  approvedUpcoming: number;
  pending: number;
  available: number | null;
};

export type LeaveListItem = {
  id: string;
  employeeId: string;
  employeeName: string;
  employeeCode: string;
  leaveTypeId: string;
  leaveTypeName: string;
  startIso: string;
  endIso: string;
  requestedDays: number;
  status: LeaveRequestStatus;
  reason: string;
  reviewComment: string | null;
  submittedAt: string;
  canCancel: boolean;
};

async function audit(
  db: Db,
  entry: {
    actorUserId: string;
    action: string;
    entityType: string;
    entityId: string;
    metadata?: Prisma.InputJsonValue;
  },
) {
  await db.auditLog.create({ data: entry });
}

export async function getBalanceCards(employeeId: string): Promise<BalanceCard[]> {
  const organization = await getOrganization();
  const today = todayIso(organization.timezone);
  const yearStart = leaveYearStartIso(
    today,
    organization.leaveYearStartMonth,
    organization.leaveYearStartDay,
  );
  const yearDate = dateOnly(yearStart);

  const [types, entitlements, adjustments, requests] = await Promise.all([
    prisma.leaveType.findMany({ orderBy: [{ sortOrder: "asc" }, { name: "asc" }] }),
    prisma.leaveEntitlement.findMany({ where: { employeeId, yearStart: yearDate } }),
    prisma.leaveBalanceAdjustment.findMany({ where: { employeeId, yearStart: yearDate } }),
    prisma.leaveRequest.findMany({
      where: {
        employeeId,
        yearStart: yearDate,
        status: { in: ["PENDING", "APPROVED"] },
      },
      include: { days: true },
    }),
  ]);

  const usedTypeIds = new Set(requests.map((request) => request.leaveTypeId));
  const visible = types.filter((type) => type.isActive || usedTypeIds.has(type.id));

  return visible.map((type) => {
    const entitlement = days(
      entitlements.find((row) => row.leaveTypeId === type.id)?.entitledDays,
    );
    const adjustmentTotal = roundDay(
      adjustments
        .filter((row) => row.leaveTypeId === type.id)
        .reduce((sum, row) => sum + days(row.adjustmentDays), 0),
    );
    let approvedTaken = 0;
    let approvedUpcoming = 0;
    let pending = 0;
    for (const request of requests.filter((row) => row.leaveTypeId === type.id)) {
      for (const day of request.days) {
        const portion = days(day.portion);
        if (request.status === "PENDING") pending += portion;
        else if (isoFromDateOnly(day.leaveDate) <= today) approvedTaken += portion;
        else approvedUpcoming += portion;
      }
    }
    const balance = calculateBalance({
      tracksBalance: type.tracksBalance,
      allowsNegative: type.allowsNegativeBalance,
      entitlement,
      adjustments: adjustmentTotal,
      approvedTaken,
      approvedUpcoming,
      pending,
    });
    return {
      leaveTypeId: type.id,
      name: type.name,
      tracksBalance: type.tracksBalance,
      entitlement: balance.entitlement,
      adjustments: balance.adjustments,
      approvedTaken: balance.approvedTaken,
      approvedUpcoming: balance.approvedUpcoming,
      pending: balance.pending,
      available: balance.available,
    };
  });
}

function toListItem(
  request: {
    id: string;
    employeeId: string;
    leaveTypeId: string;
    startDate: Date;
    endDate: Date;
    requestedDays: Prisma.Decimal;
    status: LeaveRequestStatus;
    reason: string;
    reviewComment: string | null;
    submittedAt: Date;
    employee: { fullName: string; employeeCode: string };
    leaveType: { name: string };
  },
  canCancel: boolean,
): LeaveListItem {
  return {
    id: request.id,
    employeeId: request.employeeId,
    employeeName: request.employee.fullName,
    employeeCode: request.employee.employeeCode,
    leaveTypeId: request.leaveTypeId,
    leaveTypeName: request.leaveType.name,
    startIso: isoFromDateOnly(request.startDate),
    endIso: isoFromDateOnly(request.endDate),
    requestedDays: days(request.requestedDays),
    status: request.status,
    reason: request.reason,
    reviewComment: request.reviewComment,
    submittedAt: request.submittedAt.toISOString(),
    canCancel,
  };
}

export async function listLeaveRequests(scope: { employeeId?: string }) {
  const organization = await getOrganization();
  const today = todayIso(organization.timezone);
  const requests = await prisma.leaveRequest.findMany({
    where: scope.employeeId ? { employeeId: scope.employeeId } : {},
    include: { employee: true, leaveType: true },
    orderBy: { submittedAt: "desc" },
  });
  return requests.map((request) =>
    toListItem(
      request,
      employeeCanCancelRequest(request.status, isoFromDateOnly(request.startDate), today, organization),
    ),
  );
}

export async function submitLeaveRequest(input: {
  actorUserId: string;
  employeeId: string;
  leaveTypeId: string;
  startIso: string;
  endIso: string;
  startPortion: DayPortion;
  endPortion: DayPortion;
  reason: string;
  idempotencyKey: string;
}): Promise<ServiceResult<{ id: string; requestedDays: number }>> {
  if (!isIsoDate(input.startIso) || !isIsoDate(input.endIso)) {
    return fail("Enter a valid start and end date.");
  }

  const organization = await getOrganization();
  const yearStart = leaveYearStartIso(
    input.startIso,
    organization.leaveYearStartMonth,
    organization.leaveYearStartDay,
  );
  const endYear = leaveYearStartIso(
    input.endIso,
    organization.leaveYearStartMonth,
    organization.leaveYearStartDay,
  );
  if (yearStart !== endYear) {
    return fail("This request crosses a leave year. Submit each leave year separately.");
  }

  try {
    return await prisma.$transaction(async (tx) => {
      await tx.$queryRaw`SELECT "id" FROM "Employee" WHERE "id" = ${input.employeeId} FOR UPDATE`;

      const existing = await tx.leaveRequest.findUnique({
        where: { idempotencyKey: input.idempotencyKey },
      });
      if (existing) {
        if (existing.employeeId !== input.employeeId) {
          return fail("This submission could not be saved.");
        }
        return ok({ id: existing.id, requestedDays: days(existing.requestedDays) });
      }

      const employee = await tx.employee.findUnique({ where: { id: input.employeeId } });
      if (!employee || employee.employmentStatus !== "ACTIVE") {
        return fail("This employee cannot request leave.");
      }
      if (employee.userId !== input.actorUserId) {
        return fail("You can only request leave for yourself.");
      }

      const leaveType = await tx.leaveType.findUnique({ where: { id: input.leaveTypeId } });
      if (!leaveType || !leaveType.isActive) {
        return fail("Choose an active leave type.");
      }
      if (leaveType.requiresReason && input.reason.trim().length === 0) {
        return fail("A reason is required for this leave type.");
      }

      const holidays = await tx.holiday.findMany({
        where: {
          isActive: true,
          holidayDate: { gte: dateOnly(input.startIso), lte: dateOnly(input.endIso) },
        },
      });
      const counted = countLeaveDays({
        startIso: input.startIso,
        endIso: input.endIso,
        startPortion: input.startPortion,
        endPortion: input.endPortion,
        weekendDays: organization.weekendDays,
        holidayIsos: holidays.map((holiday) => isoFromDateOnly(holiday.holidayDate)),
        allowsHalfDay: leaveType.allowsHalfDay,
      });
      if (!counted.ok) return counted;

      const overlap = await tx.leaveRequestDay.findFirst({
        where: {
          leaveDate: { in: counted.days.map((day) => dateOnly(day.iso)) },
          leaveRequest: {
            employeeId: input.employeeId,
            status: { in: ["PENDING", "APPROVED"] },
          },
        },
      });
      if (overlap) {
        return fail("Those dates overlap an existing leave request.");
      }

      const yearDate = dateOnly(yearStart);
      const [entitlement, adjustments, openRequests] = await Promise.all([
        tx.leaveEntitlement.findUnique({
          where: {
            employeeId_leaveTypeId_yearStart: {
              employeeId: input.employeeId,
              leaveTypeId: leaveType.id,
              yearStart: yearDate,
            },
          },
        }),
        tx.leaveBalanceAdjustment.findMany({
          where: { employeeId: input.employeeId, leaveTypeId: leaveType.id, yearStart: yearDate },
        }),
        tx.leaveRequest.findMany({
          where: {
            employeeId: input.employeeId,
            leaveTypeId: leaveType.id,
            yearStart: yearDate,
            status: { in: ["PENDING", "APPROVED"] },
          },
          include: { days: true },
        }),
      ]);

      const today = todayIso(organization.timezone);
      let approvedTaken = 0;
      let approvedUpcoming = 0;
      let pending = 0;
      for (const request of openRequests) {
        for (const day of request.days) {
          const portion = days(day.portion);
          if (request.status === "PENDING") pending += portion;
          else if (isoFromDateOnly(day.leaveDate) <= today) approvedTaken += portion;
          else approvedUpcoming += portion;
        }
      }
      const balanceInput = {
        tracksBalance: leaveType.tracksBalance,
        allowsNegative: leaveType.allowsNegativeBalance,
        entitlement: days(entitlement?.entitledDays),
        adjustments: roundDay(adjustments.reduce((sum, row) => sum + days(row.adjustmentDays), 0)),
        approvedTaken,
        approvedUpcoming,
        pending,
      };
      if (requestExceedsBalance(balanceInput, counted.requestedDays)) {
        return fail("This request exceeds the available leave balance.");
      }

      const created = await tx.leaveRequest.create({
        data: {
          employeeId: input.employeeId,
          leaveTypeId: leaveType.id,
          yearStart: yearDate,
          startDate: dateOnly(input.startIso),
          endDate: dateOnly(input.endIso),
          startPortion: input.startPortion,
          endPortion: input.startIso === input.endIso ? input.startPortion : input.endPortion,
          requestedDays: counted.requestedDays.toFixed(1),
          reason: input.reason.trim(),
          status: "PENDING",
          idempotencyKey: input.idempotencyKey,
          days: {
            create: counted.days.map((day) => ({
              leaveDate: dateOnly(day.iso),
              portion: day.portion.toFixed(1),
            })),
          },
        },
      });

      await audit(tx, {
        actorUserId: input.actorUserId,
        action: "leave.submitted",
        entityType: "LeaveRequest",
        entityId: created.id,
        metadata: { requestedDays: counted.requestedDays, leaveType: leaveType.name },
      });

      return ok({ id: created.id, requestedDays: counted.requestedDays });
    });
  } catch (error) {
    if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002") {
      const existing = await prisma.leaveRequest.findUnique({
        where: { idempotencyKey: input.idempotencyKey },
      });
      if (existing && existing.employeeId === input.employeeId) {
        return ok({ id: existing.id, requestedDays: days(existing.requestedDays) });
      }
    }
    throw error;
  }
}

export async function reviewLeaveRequest(input: {
  actorUserId: string;
  requestId: string;
  decision: "APPROVED" | "REJECTED";
  comment: string;
}): Promise<ServiceResult<{ id: string }>> {
  const comment = input.comment.trim();
  if (input.decision === "REJECTED" && comment.length === 0) {
    return fail("Add a comment when rejecting a request.");
  }

  return prisma.$transaction(async (tx) => {
    const request = await tx.leaveRequest.findUnique({
      where: { id: input.requestId },
      include: { employee: true },
    });
    if (!request) return fail("That leave request could not be found.");
    if (request.status !== "PENDING") return fail("Only a pending request can be reviewed.");
    if (request.employee.userId === input.actorUserId) {
      return fail("You cannot review your own leave request.");
    }

    await tx.$queryRaw`SELECT "id" FROM "Employee" WHERE "id" = ${request.employeeId} FOR UPDATE`;
    await tx.leaveRequest.update({
      where: { id: request.id },
      data: {
        status: input.decision,
        reviewedByUserId: input.actorUserId,
        reviewedAt: new Date(),
        reviewComment: comment || null,
      },
    });
    await audit(tx, {
      actorUserId: input.actorUserId,
      action: input.decision === "APPROVED" ? "leave.approved" : "leave.rejected",
      entityType: "LeaveRequest",
      entityId: request.id,
      metadata: { status: input.decision },
    });
    return ok({ id: request.id });
  });
}

export async function cancelLeaveRequest(input: {
  actorUserId: string;
  actorRole: "EMPLOYEE" | "ADMINISTRATOR" | "MANAGER";
  requestId: string;
}): Promise<ServiceResult<{ id: string }>> {
  const organization = await getOrganization();
  const today = todayIso(organization.timezone);

  return prisma.$transaction(async (tx) => {
    const request = await tx.leaveRequest.findUnique({
      where: { id: input.requestId },
      include: { employee: true },
    });
    if (!request) return fail("That leave request could not be found.");

    const isOwner = request.employee.userId === input.actorUserId;
    if (!isOwner && input.actorRole !== "ADMINISTRATOR") {
      return fail("You do not have permission to cancel this request.");
    }
    if (request.status !== "PENDING" && request.status !== "APPROVED") {
      return fail("This request can no longer be cancelled.");
    }
    if (
      isOwner &&
      input.actorRole !== "ADMINISTRATOR" &&
      !employeeCanCancelRequest(request.status, isoFromDateOnly(request.startDate), today, organization)
    ) {
      return fail("This request can no longer be cancelled.");
    }

    await tx.leaveRequest.update({
      where: { id: request.id },
      data: {
        status: "CANCELLED",
        cancelledByUserId: input.actorUserId,
        cancelledAt: new Date(),
      },
    });
    await audit(tx, {
      actorUserId: input.actorUserId,
      action: "leave.cancelled",
      entityType: "LeaveRequest",
      entityId: request.id,
    });
    return ok({ id: request.id });
  });
}
