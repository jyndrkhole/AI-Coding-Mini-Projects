import assert from "node:assert/strict";
import test from "node:test";
import { leaveYearStartIso, monthBoundsIso, startOfZonedDay, todayIso } from "./dates";

test("a January leave year uses the same calendar year", () => {
  assert.equal(leaveYearStartIso("2026-10-30", 1, 1), "2026-01-01");
});

test("an April leave year rolls back before the start date", () => {
  assert.equal(leaveYearStartIso("2026-10-30", 4, 1), "2026-04-01");
  assert.equal(leaveYearStartIso("2026-02-01", 4, 1), "2025-04-01");
});

test("month bounds use the first and last calendar day", () => {
  assert.deepEqual(monthBoundsIso("2026-11-02"), { fromIso: "2026-11-01", toIso: "2026-11-30" });
  assert.deepEqual(monthBoundsIso("2024-02-10"), { fromIso: "2024-02-01", toIso: "2024-02-29" });
});

test("today in Asia/Kolkata is the local calendar date", () => {
  const instant = new Date("2026-10-29T20:30:00.000Z");
  assert.equal(todayIso("Asia/Kolkata", instant), "2026-10-30");
});

test("the start of an India calendar day is 18:30 UTC the previous day", () => {
  assert.equal(
    startOfZonedDay("2026-10-30", "Asia/Kolkata").toISOString(),
    "2026-10-29T18:30:00.000Z",
  );
});
