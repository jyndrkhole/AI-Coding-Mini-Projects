import { roundDay } from "./dates";

export type BalanceInput = {
  tracksBalance: boolean;
  allowsNegative: boolean;
  entitlement: number;
  adjustments: number;
  approvedTaken: number;
  approvedUpcoming: number;
  pending: number;
};

export type BalanceResult = {
  entitlement: number;
  adjustments: number;
  approvedTaken: number;
  approvedUpcoming: number;
  approved: number;
  pending: number;
  available: number | null;
};

export function calculateBalance(input: BalanceInput): BalanceResult {
  const entitlement = roundDay(input.entitlement);
  const adjustments = roundDay(input.adjustments);
  const approvedTaken = roundDay(input.approvedTaken);
  const approvedUpcoming = roundDay(input.approvedUpcoming);
  const pending = roundDay(input.pending);
  const approved = roundDay(approvedTaken + approvedUpcoming);
  return {
    entitlement,
    adjustments,
    approvedTaken,
    approvedUpcoming,
    approved,
    pending,
    available: input.tracksBalance
      ? roundDay(entitlement + adjustments - approved)
      : null,
  };
}

/** Pending days are reserved here so two open requests cannot oversubscribe a balance. */
export function requestExceedsBalance(input: BalanceInput, requestedDays: number): boolean {
  if (!input.tracksBalance || input.allowsNegative) return false;
  const balance = calculateBalance(input);
  const available = balance.available ?? 0;
  return roundDay(requestedDays) > roundDay(available - balance.pending);
}
