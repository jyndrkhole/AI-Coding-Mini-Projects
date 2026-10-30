import assert from "node:assert/strict";
import test from "node:test";
import { countLeaveDays } from "./leave-days";

const weekends = [0, 6];

test("counts a single working day", () => {
  const result = countLeaveDays({
    startIso: "2026-11-10",
    endIso: "2026-11-10",
    startPortion: "FULL",
    endPortion: "FULL",
    weekendDays: weekends,
    holidayIsos: [],
    allowsHalfDay: false,
  });
  assert.equal(result.ok, true);
  if (result.ok) assert.equal(result.requestedDays, 1);
});

test("skips Saturday and Sunday", () => {
  const result = countLeaveDays({
    startIso: "2026-11-06",
    endIso: "2026-11-09",
    startPortion: "FULL",
    endPortion: "FULL",
    weekendDays: weekends,
    holidayIsos: [],
    allowsHalfDay: false,
  });
  assert.equal(result.ok, true);
  if (result.ok) {
    assert.equal(result.requestedDays, 2);
    assert.deepEqual(
      result.days.map((day) => day.iso),
      ["2026-11-06", "2026-11-09"],
    );
  }
});

test("skips a configured holiday", () => {
  const result = countLeaveDays({
    startIso: "2026-11-10",
    endIso: "2026-11-10",
    startPortion: "FULL",
    endPortion: "FULL",
    weekendDays: weekends,
    holidayIsos: ["2026-11-10"],
    allowsHalfDay: false,
  });
  assert.equal(result.ok, false);
});

test("counts a half day when the leave type allows it", () => {
  const result = countLeaveDays({
    startIso: "2026-11-10",
    endIso: "2026-11-10",
    startPortion: "AM",
    endPortion: "FULL",
    weekendDays: weekends,
    holidayIsos: [],
    allowsHalfDay: true,
  });
  assert.equal(result.ok, true);
  if (result.ok) assert.equal(result.requestedDays, 0.5);
});

test("rejects a half day when the leave type does not allow it", () => {
  const result = countLeaveDays({
    startIso: "2026-11-10",
    endIso: "2026-11-10",
    startPortion: "PM",
    endPortion: "PM",
    weekendDays: weekends,
    holidayIsos: [],
    allowsHalfDay: false,
  });
  assert.equal(result.ok, false);
});

test("rejects an end date before the start date", () => {
  const result = countLeaveDays({
    startIso: "2026-11-11",
    endIso: "2026-11-10",
    startPortion: "FULL",
    endPortion: "FULL",
    weekendDays: weekends,
    holidayIsos: [],
    allowsHalfDay: false,
  });
  assert.equal(result.ok, false);
});
