import { Prisma } from "@prisma/client";
import { dateOnly, leaveYearStartIso, todayIso } from "@/lib/dates";
import { hashPassword } from "@/server/auth/password";
import { prisma } from "@/server/db";
import { getOrganization } from "@/server/services/organization";
import type { ServiceResult } from "@/server/services/leave";

function fail(error: string): ServiceResult<never> {
  return { ok: false, error };
}

export async function createEmployee(input: {
  actorUserId: string;
  employeeCode: string;
  fullName: string;
  email: string;
  department: string;
  designation: string;
  joiningDate: string;
  role: "EMPLOYEE" | "ADMINISTRATOR";
  password: string;
}): Promise<ServiceResult<{ id: string }>> {
  const email = input.email.trim().toLowerCase();
  const employeeCode = input.employeeCode.trim();
  const fullName = input.fullName.trim();
  if (!employeeCode || !fullName || !email || !input.department.trim() || !input.designation.trim()) {
    return fail("Fill in every required field.");
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(input.joiningDate)) {
    return fail("Enter a valid joining date.");
  }
  if (input.password.length < 10) {
    return fail("The temporary password must be at least 10 characters.");
  }

  const organization = await getOrganization();
  const yearStart = dateOnly(
    leaveYearStartIso(todayIso(organization.timezone), organization.leaveYearStartMonth, organization.leaveYearStartDay),
  );
  const passwordHash = await hashPassword(input.password);

  try {
    const created = await prisma.$transaction(async (tx) => {
      const user = await tx.user.create({
        data: {
          email,
          passwordHash,
          role: input.role,
          employee: {
            create: {
              employeeCode,
              fullName,
              department: input.department.trim(),
              designation: input.designation.trim(),
              joiningDate: dateOnly(input.joiningDate),
            },
          },
        },
        include: { employee: true },
      });
      const employee = user.employee;
      if (!employee) throw new Error("Employee profile was not created.");

      const leaveTypes = await tx.leaveType.findMany({ where: { isActive: true } });
      if (leaveTypes.length > 0) {
        await tx.leaveEntitlement.createMany({
          data: leaveTypes.map((leaveType) => ({
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
          action: "employee.created",
          entityType: "Employee",
          entityId: employee.id,
          metadata: { employeeCode, role: input.role },
        },
      });
      return employee;
    });
    return { ok: true, value: { id: created.id } };
  } catch (error) {
    if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002") {
      return fail("That employee ID or email is already in use.");
    }
    throw error;
  }
}

export async function setEmploymentStatus(input: {
  actorUserId: string;
  employeeId: string;
  status: "ACTIVE" | "INACTIVE";
}): Promise<ServiceResult<{ id: string }>> {
  const employee = await prisma.employee.findUnique({
    where: { id: input.employeeId },
    include: { user: true },
  });
  if (!employee) return fail("That employee could not be found.");
  if (employee.userId === input.actorUserId && input.status === "INACTIVE") {
    return fail("You cannot deactivate your own account.");
  }
  if (employee.user.role === "ADMINISTRATOR" && input.status === "INACTIVE") {
    const otherAdmins = await prisma.user.count({
      where: { role: "ADMINISTRATOR", isActive: true, id: { not: employee.userId } },
    });
    if (otherAdmins === 0) return fail("Keep at least one active administrator.");
  }

  await prisma.$transaction(async (tx) => {
    await tx.employee.update({
      where: { id: employee.id },
      data: { employmentStatus: input.status },
    });
    await tx.user.update({
      where: { id: employee.userId },
      data: { isActive: input.status === "ACTIVE" },
    });
    if (input.status === "INACTIVE") {
      await tx.session.deleteMany({ where: { userId: employee.userId } });
    }
    await tx.auditLog.create({
      data: {
        actorUserId: input.actorUserId,
        action: input.status === "ACTIVE" ? "employee.activated" : "employee.deactivated",
        entityType: "Employee",
        entityId: employee.id,
      },
    });
  });

  return { ok: true, value: { id: employee.id } };
}
