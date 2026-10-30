export type CancellationPolicy = {
  employeeCanCancelPending: boolean;
  employeeCanCancelApproved: boolean;
  cancelApprovedBeforeStartOnly: boolean;
};

export function employeeCanCancelRequest(
  status: "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED",
  startIso: string,
  today: string,
  policy: CancellationPolicy,
): boolean {
  if (status === "PENDING") return policy.employeeCanCancelPending;
  if (status !== "APPROVED" || !policy.employeeCanCancelApproved) return false;
  if (!policy.cancelApprovedBeforeStartOnly) return true;
  return startIso > today;
}
