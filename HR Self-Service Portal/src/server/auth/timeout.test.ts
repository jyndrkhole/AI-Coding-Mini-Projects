import assert from "node:assert/strict";
import test from "node:test";
import { SESSION_IDLE_MS, sessionTimedOut } from "./timeout";

test("a session stays open during the idle window", () => {
  const now = new Date("2026-11-02T08:00:00.000Z");
  assert.equal(
    sessionTimedOut(
      { expiresAt: new Date(now.getTime() + 60 * 60 * 1000), lastSeenAt: new Date(now.getTime() - SESSION_IDLE_MS) },
      now,
    ),
    false,
  );
});

test("a session closes after 30 minutes without activity", () => {
  const now = new Date("2026-11-02T08:00:00.000Z");
  assert.equal(
    sessionTimedOut(
      {
        expiresAt: new Date(now.getTime() + 60 * 60 * 1000),
        lastSeenAt: new Date(now.getTime() - SESSION_IDLE_MS - 1),
      },
      now,
    ),
    true,
  );
});

test("a session closes at the 12 hour limit even when it was just used", () => {
  const now = new Date("2026-11-02T08:00:00.000Z");
  assert.equal(sessionTimedOut({ expiresAt: now, lastSeenAt: now }, now), true);
});
