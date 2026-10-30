import assert from "node:assert/strict";
import test from "node:test";
import { calculateBalance, requestExceedsBalance, type BalanceInput } from "./balance";

const base: BalanceInput = {
  tracksBalance: true,
  allowsNegative: false,
  entitlement: 12,
  adjustments: 0,
  approvedTaken: 2,
  approvedUpcoming: 1,
  pending: 1,
};

test("available balance excludes pending and keeps future approved leave visible", () => {
  const balance = calculateBalance(base);
  assert.equal(balance.available, 9);
  assert.equal(balance.approved, 3);
  assert.equal(balance.pending, 1);
});

test("a new request can use what remains after pending reservations", () => {
  assert.equal(requestExceedsBalance(base, 8), false);
  assert.equal(requestExceedsBalance(base, 8.5), true);
});

test("adjustments change the available balance", () => {
  const balance = calculateBalance({ ...base, adjustments: 1.5 });
  assert.equal(balance.available, 10.5);
});

test("unpaid leave without a tracked balance is not capped", () => {
  const input = { ...base, tracksBalance: false, entitlement: 0 };
  assert.equal(calculateBalance(input).available, null);
  assert.equal(requestExceedsBalance(input, 20), false);
});

test("negative balances can be allowed by the leave type", () => {
  assert.equal(requestExceedsBalance({ ...base, allowsNegative: true }, 40), false);
});
