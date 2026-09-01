import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";
import { env, PROJECT_ROOT } from "../config/env.ts";
import { WEBHOOK_EVENTS_SCHEMA } from "./schema.ts";

let db: Database.Database | null = null;

function resolveDatabasePath(databasePath: string): string {
  if (databasePath === ":memory:") {
    return databasePath;
  }
  return path.isAbsolute(databasePath) ? databasePath : path.join(PROJECT_ROOT, databasePath);
}

export function initDb(databasePath = env.databasePath): Database.Database {
  if (db) {
    return db;
  }
  const resolved = resolveDatabasePath(databasePath);
  if (resolved !== ":memory:") {
    fs.mkdirSync(path.dirname(resolved), { recursive: true });
  }
  db = new Database(resolved);
  db.pragma("journal_mode = WAL");
  db.exec(WEBHOOK_EVENTS_SCHEMA);
  return db;
}

export function getDb(): Database.Database {
  if (!db) {
    return initDb();
  }
  return db;
}

export function closeDb(): void {
  if (db) {
    db.close();
    db = null;
  }
}

export function resetDb(): void {
  const connection = getDb();
  connection.exec("DELETE FROM webhook_events");
}
