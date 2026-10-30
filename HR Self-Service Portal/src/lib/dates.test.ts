import assert from "node:assert/strict";
import test from "node:test";
import { leaveYearStartIso, startOfZonedDay, todayIso } from "./dates";

test("a January leave year uses the same calendar year", () => {
  assert.equal(leaveYearStartIso("2026-10-30", 1, 1), "2026-01-01");
});

test("an April leave year rolls back before the start date", () => {
  assert.equal(leaveYearStartIso("2026-10-30", 4, 1), "2026-04-01");
  assert.equal(leaveYearStartIso("2026-02-01", 4, 1), "2025-04-01");
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
