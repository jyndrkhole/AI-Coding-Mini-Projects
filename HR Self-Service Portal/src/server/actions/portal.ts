"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import type { DayPortion } from "@prisma/client";
import { requireAdmin, requireUser } from "@/server/auth/guard";
import { adjustBalance, createHoliday, createLeaveType } from "@/server/services/catalog";
import { createEmployee, setEmploymentStatus } from "@/server/services/employees";
import { cancelLeaveRequest, reviewLeaveRequest, submitLeaveRequest } from "@/server/services/leave";

export type ActionState = { error: string };

const portions = new Set(["FULL", "AM", "PM"]);

function rethrowRedirect(error: unknown): void {
  if (
    typeof error === "object" &&
    error !== null &&
    "digest" in error &&
    String((error as { digest?: unknown }).digest).startsWith("NEXT_REDIRECT")
  ) {
    throw error;
  }
}

export async function submitLeaveAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  const session = await requireUser();
  const employeeId = session.user.employee?.id;
  if (!employeeId) return { error: "Your employee profile is missing." };

  const startPortion = String(formData.get("startPortion") ?? "FULL");
  const endPortion = String(formData.get("endPortion") ?? "FULL");
  if (!portions.has(startPortion) || !portions.has(endPortion)) {
    return { error: "Choose a valid portion of the day." };
  }

  const result = await submitLeaveRequest({
    actorUserId: session.userId,
    employeeId,
    leaveTypeId: String(formData.get("leaveTypeId") ?? ""),
    startIso: String(formData.get("startDate") ?? ""),
    endIso: String(formData.get("endDate") ?? ""),
    startPortion: startPortion as DayPortion,
    endPortion: endPortion as DayPortion,
    reason: String(formData.get("reason") ?? ""),
    idempotencyKey: String(formData.get("idempotencyKey") ?? ""),
  });
  if (!result.ok) return { error: result.error };

  revalidatePath("/dashboard");
  revalidatePath("/leave");
  revalidatePath("/admin");
  redirect(`/leave?notice=submitted&days=${result.value.requestedDays}`);
}

export async function cancelLeaveAction(formData: FormData) {
  const session = await requireUser();
  const result = await cancelLeaveRequest({
    actorUserId: session.userId,
    actorRole: session.user.role,
    requestId: String(formData.get("requestId") ?? ""),
  });
  if (!result.ok) redirect(`/leave?error=${encodeURIComponent(result.error)}`);
  revalidatePath("/dashboard");
  revalidatePath("/leave");
  revalidatePath("/admin");
  redirect("/leave?notice=cancelled");
}

export async function reviewLeaveAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  const session = await requireAdmin();
  const decision = String(formData.get("decision") ?? "");
  if (decision !== "APPROVED" && decision !== "REJECTED") {
    return { error: "Choose approve or reject." };
  }
  const result = await reviewLeaveRequest({
    actorUserId: session.userId,
    requestId: String(formData.get("requestId") ?? ""),
    decision,
    comment: String(formData.get("comment") ?? ""),
  });
  if (!result.ok) return { error: result.error };
  revalidatePath("/admin");
  revalidatePath("/dashboard");
  revalidatePath("/leave");
  redirect(decision === "APPROVED" ? "/admin/leave?notice=approved" : "/admin/leave?notice=rejected");
}

export async function createLeaveTypeAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  const session = await requireAdmin();
  const result = await createLeaveType({
    actorUserId: session.userId,
    name: String(formData.get("name") ?? ""),
    description: String(formData.get("description") ?? ""),
    isPaid: formData.get("isPaid") === "on",
    tracksBalance: formData.get("tracksBalance") === "on",
    defaultAnnualEntitlement: Number(formData.get("defaultAnnualEntitlement") ?? 0),
    allowsHalfDay: formData.get("allowsHalfDay") === "on",
    allowsNegativeBalance: formData.get("allowsNegativeBalance") === "on",
    carryForwardEligible: formData.get("carryForwardEligible") === "on",
    maxCarryForwardDays: formData.get("maxCarryForwardDays")
      ? Number(formData.get("maxCarryForwardDays"))
      : null,
    requiresReason: formData.get("requiresReason") === "on",
  });
  if (!result.ok) return { error: result.error };
  revalidatePath("/admin/policies");
  revalidatePath("/dashboard");
  redirect("/admin/policies?notice=leave-type");
}

export async function createEmployeeAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  const session = await requireAdmin();
  const role = String(formData.get("role") ?? "EMPLOYEE");
  if (role !== "EMPLOYEE" && role !== "ADMINISTRATOR") {
    return { error: "Choose a valid role." };
  }
  const result = await createEmployee({
    actorUserId: session.userId,
    employeeCode: String(formData.get("employeeCode") ?? ""),
    fullName: String(formData.get("fullName") ?? ""),
    email: String(formData.get("email") ?? ""),
    department: String(formData.get("department") ?? ""),
    designation: String(formData.get("designation") ?? ""),
    joiningDate: String(formData.get("joiningDate") ?? ""),
    role,
    password: String(formData.get("password") ?? ""),
  });
  if (!result.ok) return { error: result.error };
  revalidatePath("/admin/employees");
  redirect(`/admin/employees/${result.value.id}?notice=employee`);
}

export async function setEmploymentStatusAction(formData: FormData) {
  const session = await requireAdmin();
  const status = String(formData.get("status") ?? "");
  if (status !== "ACTIVE" && status !== "INACTIVE") redirect("/admin/employees");
  const employeeId = String(formData.get("employeeId") ?? "");
  const result = await setEmploymentStatus({
    actorUserId: session.userId,
    employeeId,
    status,
  });
  revalidatePath("/admin/employees");
  if (!result.ok) redirect(`/admin/employees/${employeeId}?error=${encodeURIComponent(result.error)}`);
  redirect(`/admin/employees/${employeeId}?notice=status`);
}

export async function adjustBalanceAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  const session = await requireAdmin();
  const result = await adjustBalance({
    actorUserId: session.userId,
    employeeId: String(formData.get("employeeId") ?? ""),
    leaveTypeId: String(formData.get("leaveTypeId") ?? ""),
    adjustmentDays: Number(formData.get("adjustmentDays") ?? 0),
    reason: String(formData.get("reason") ?? ""),
  });
  if (!result.ok) return { error: result.error };
  revalidatePath("/admin/balances");
  revalidatePath("/dashboard");
  redirect("/admin/balances?notice=balance");
}

export async function createHolidayAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  const session = await requireAdmin();
  try {
    const result = await createHoliday({
      actorUserId: session.userId,
      name: String(formData.get("name") ?? ""),
      holidayDate: String(formData.get("holidayDate") ?? ""),
    });
    if (!result.ok) return { error: result.error };
    revalidatePath("/admin/policies");
    redirect("/admin/policies?notice=holiday");
  } catch (error) {
    rethrowRedirect(error);
    return { error: "The holiday could not be saved." };
  }
}
