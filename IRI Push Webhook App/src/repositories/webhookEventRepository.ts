import { randomUUID } from "node:crypto";
import { getDb } from "../database/db.ts";
import { displayNameForEventType, isKnownEventType } from "../config/eventsCatalog.ts";
import type {
  DashboardStats,
  EventListFilters,
  EventListResult,
  WebhookEvent,
  WebhookEventRow
} from "../types/index.ts";

function parseJson(value: string | null): unknown {
  if (value === null || value === "") {
    return null;
  }
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

export function mapWebhookEvent(row: WebhookEventRow): WebhookEvent {
  return {
    id: row.id,
    eventType: row.event_type,
    policyNumber: row.policy_number,
    receivedAt: row.received_at,
    requestMethod: row.request_method,
    requestPath: row.request_path,
    headers: parseJson(row.headers_json) as Record<string, string>,
    payload: parseJson(row.payload_json),
    sourceIp: row.source_ip,
    responseStatus: row.response_status,
    responseBody: parseJson(row.response_body),
    processingTimeMs: row.processing_time_ms,
    createdAt: row.created_at,
    knownEvent: isKnownEventType(row.event_type),
    displayName: displayNameForEventType(row.event_type)
  };
}

export interface InsertWebhookEventInput {
  id?: string;
  eventType: string | null;
  policyNumber: string | null;
  receivedAt: string;
  requestMethod: string;
  requestPath: string;
  headers: Record<string, string>;
  payload: unknown;
  sourceIp: string | null;
  responseStatus: number;
  responseBody: unknown;
  processingTimeMs: number;
}

export function insertWebhookEvent(input: InsertWebhookEventInput): WebhookEvent {
  const id = input.id ?? randomUUID();
  const createdAt = new Date().toISOString();
  getDb()
    .prepare(
      `INSERT INTO webhook_events (
        id, event_type, policy_number, received_at, request_method, request_path,
        headers_json, payload_json, source_ip, response_status, response_body,
        processing_time_ms, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .run(
      id,
      input.eventType,
      input.policyNumber,
      input.receivedAt,
      input.requestMethod,
      input.requestPath,
      JSON.stringify(input.headers),
      input.payload === undefined ? null : JSON.stringify(input.payload),
      input.sourceIp,
      input.responseStatus,
      JSON.stringify(input.responseBody),
      input.processingTimeMs,
      createdAt
    );

  return getWebhookEventById(id)!;
}

export function getWebhookEventById(id: string): WebhookEvent | undefined {
  const row = getDb().prepare("SELECT * FROM webhook_events WHERE id = ?").get(id) as WebhookEventRow | undefined;
  return row ? mapWebhookEvent(row) : undefined;
}

export function listWebhookEvents(filters: EventListFilters = {}): EventListResult {
  const where: string[] = [];
  const params: unknown[] = [];

  if (filters.eventType) {
    where.push("event_type = ?");
    params.push(filters.eventType);
  }
  if (filters.policyNumber) {
    where.push("policy_number LIKE ?");
    params.push(`%${filters.policyNumber}%`);
  }
  if (filters.status !== undefined) {
    where.push("response_status = ?");
    params.push(filters.status);
  }
  if (filters.from) {
    where.push("received_at >= ?");
    params.push(filters.from);
  }
  if (filters.to) {
    where.push("received_at <= ?");
    params.push(filters.to);
  }
  if (filters.search) {
    where.push("(event_type LIKE ? OR policy_number LIKE ? OR payload_json LIKE ? OR id LIKE ?)");
    const term = `%${filters.search}%`;
    params.push(term, term, term, term);
  }

  const whereSql = where.length > 0 ? `WHERE ${where.join(" AND ")}` : "";
  const limit = Math.min(Math.max(filters.limit ?? 50, 1), 200);
  const offset = Math.max(filters.offset ?? 0, 0);

  const totalRow = getDb()
    .prepare(`SELECT COUNT(*) AS count FROM webhook_events ${whereSql}`)
    .get(...params) as { count: number };

  const rows = getDb()
    .prepare(
      `SELECT * FROM webhook_events ${whereSql} ORDER BY received_at DESC LIMIT ? OFFSET ?`
    )
    .all(...params, limit, offset) as WebhookEventRow[];

  return {
    total: totalRow.count,
    events: rows.map(mapWebhookEvent)
  };
}

export function deleteAllWebhookEvents(): number {
  const result = getDb().prepare("DELETE FROM webhook_events").run();
  return result.changes;
}

export function getDashboardStats(): DashboardStats {
  const db = getDb();
  const totalEvents = (db.prepare("SELECT COUNT(*) AS count FROM webhook_events").get() as { count: number }).count;
  const successful = (
    db.prepare("SELECT COUNT(*) AS count FROM webhook_events WHERE response_status >= 200 AND response_status < 300").get() as {
      count: number;
    }
  ).count;
  const failed = totalEvents - successful;
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const eventsToday = (
    db.prepare("SELECT COUNT(*) AS count FROM webhook_events WHERE received_at >= ?").get(startOfToday.toISOString()) as {
      count: number;
    }
  ).count;
  const eventTypes = (
    db.prepare("SELECT COUNT(DISTINCT event_type) AS count FROM webhook_events WHERE event_type IS NOT NULL AND event_type != ''").get() as {
      count: number;
    }
  ).count;

  return { totalEvents, successful, failed, eventsToday, eventTypes };
}
