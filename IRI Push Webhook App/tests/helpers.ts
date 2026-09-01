import { afterAll, beforeEach } from "vitest";
import { createApp } from "../src/app.ts";
import { closeDb, initDb, resetDb } from "../src/database/db.ts";
import { resetRuntimeConfig } from "../src/config/runtimeConfig.ts";

export function createTestApp() {
  initDb(":memory:");
  resetRuntimeConfig();
  return createApp();
}

beforeEach(() => {
  initDb(":memory:");
  resetDb();
  resetRuntimeConfig();
});

afterAll(() => {
  closeDb();
});
