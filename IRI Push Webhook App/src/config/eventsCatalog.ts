import fs from "node:fs";
import path from "node:path";
import { env, PROJECT_ROOT } from "./env.ts";
import type { CatalogEvent, EventCatalog } from "../types/index.ts";

export function catalogPathForVersion(version = env.iriVersion): string {
  return path.join(PROJECT_ROOT, "config", "iri", version, "events.json");
}

export function loadCatalog(version = env.iriVersion): EventCatalog {
  const catalogPath = catalogPathForVersion(version);
  if (!fs.existsSync(catalogPath)) {
    throw new Error(`IRI event catalogue not found for version ${version} at ${catalogPath}`);
  }
  const parsed = JSON.parse(fs.readFileSync(catalogPath, "utf8")) as EventCatalog;
  if (!parsed.events || !Array.isArray(parsed.events)) {
    throw new Error(`IRI event catalogue at ${catalogPath} is missing an events array`);
  }
  return parsed;
}

export function findCatalogEvent(eventType: string, version = env.iriVersion): CatalogEvent | undefined {
  const catalog = loadCatalog(version);
  return catalog.events.find((event) => event.eventType === eventType);
}

export function isKnownEventType(eventType: string | null | undefined, version = env.iriVersion): boolean {
  if (!eventType) {
    return false;
  }
  try {
    return Boolean(findCatalogEvent(eventType, version));
  } catch {
    return false;
  }
}

export function displayNameForEventType(eventType: string | null | undefined): string {
  if (!eventType) {
    return "Unknown/Future Event";
  }
  const match = findCatalogEvent(eventType);
  return match?.displayName ?? "Unknown/Future Event";
}
