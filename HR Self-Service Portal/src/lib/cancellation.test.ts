import assert from "node:assert/strict";
import test from "node:test";
import { employeeCanCancelRequest, type CancellationPolicy } from "./cancellation";

const policy: CancellationPolicy = {
  employeeCanCancelPending: true,
  employeeCanCancelApproved: true,
  cancelApprovedBeforeStartOnly: true,
};

test("an employee can cancel a pending request", () => {
  assert.equal(employeeCanCancelRequest("PENDING", "2026-11-10", "2026-10-30", policy), true);
});

test("an employee can cancel approved leave that has not started", () => {
  assert.equal(employeeCanCancelRequest("APPROVED", "2026-11-10", "2026-10-30", policy), true);
  assert.equal(employeeCanCancelRequest("APPROVED", "2026-10-30", "2026-10-30", policy), false);
});

test("rejected and cancelled requests stay in history", () => {
  assert.equal(employeeCanCancelRequest("REJECTED", "2026-11-10", "2026-10-30", policy), false);
  assert.equal(employeeCanCancelRequest("CANCELLED", "2026-11-10", "2026-10-30", policy), false);
});
