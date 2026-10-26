import type { RequestHandler } from "express";
import { findPortalEventsBySourceEventIds } from "../../repositories/webhookEventRepository.ts";
import {
  fetchReconciliation,
  fetchSourceEvent,
  resolveSourceBaseUrl,
  SourceApiError
} from "../../services/sourceNotifications.ts";

function queryValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function optionalNonNegativeInt(value: unknown, field: string, minimum = 0): string | { error: string } {
  const raw = queryValue(value);
  if (!raw) {
    return "";
  }
  if (!/^\d+$/.test(raw) || Number(raw) < minimum) {
    return { error: `${field} must be an integer of ${minimum} or more` };
  }
  return raw;
}

function optionalSortOrder(value: unknown): string | { error: string } {
  const raw = queryValue(value);
  if (!raw) {
    return "";
  }
  const normalized = raw.toLowerCase();
  if (normalized !== "asc" && normalized !== "desc") {
    return { error: "sortOrder must be asc or desc" };
  }
  return normalized;
}

function requestSourceApiKey(req: { get(name: string): string | undefined }): string {
  return queryValue(req.get("x-source-api-key"));
}

function requestSourceBaseUrl(req: { get(name: string): string | undefined }): string {
  return queryValue(req.get("x-source-base-url"));
}

function sourceEventId(value: unknown): string {
  if (!value || typeof value !== "object" || !("eventId" in value)) {
    return "";
  }
  const eventId = value.eventId;
  return typeof eventId === "string" ? eventId.trim() : "";
}

function fail(error: unknown, next: (err?: unknown) => void): void {
  if (error instanceof SourceApiError) {
    next(Object.assign(error, { status: error.status }));
    return;
  }
  next(error);
}

export const reconcileNotifications: RequestHandler = async (req, res, next) => {
  try {
    const startTime = queryValue(req.query.startTime);
    const endTime = queryValue(req.query.endTime);
    if (!startTime || !endTime) {
      res.status(400).json({ status: "error", message: "startTime and endTime are required" });
      return;
    }
    const start = new Date(startTime);
    const end = new Date(endTime);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || start > end) {
      res.status(400).json({ status: "error", message: "startTime must be before endTime" });
      return;
    }

    const associatedFirmId = queryValue(req.query.associatedFirmId);
    const correlationId = queryValue(req.query.correlationId);
    const orderBy = queryValue(req.query.orderBy);
    const sortOrder = optionalSortOrder(req.query.sortOrder);
    const offset = optionalNonNegativeInt(req.query.offset, "offset");
    const limit = optionalNonNegativeInt(req.query.limit, "limit", 1);
    if (typeof sortOrder === "object") {
      res.status(400).json({ status: "error", message: sortOrder.error });
      return;
    }
    if (typeof offset === "object") {
      res.status(400).json({ status: "error", message: offset.error });
      return;
    }
    if (typeof limit === "object") {
      res.status(400).json({ status: "error", message: limit.error });
      return;
    }
    const sourceBaseUrl = requestSourceBaseUrl(req);
    const result = await fetchReconciliation({
      startTime,
      endTime,
      associatedFirmId,
      correlationId,
      orderBy,
      sortOrder,
      offset,
      limit,
      sourceApiKey: requestSourceApiKey(req),
      sourceBaseUrl
    });
    const payload = result.body && typeof result.body === "object" ? result.body : {};
    const rawEvents = "events" in payload && Array.isArray(payload.events) ? payload.events : [];
    const stored = findPortalEventsBySourceEventIds(rawEvents.map(sourceEventId));
    const events = rawEvents.map((event) => {
      const eventId = sourceEventId(event);
      const portalEventId = eventId ? stored.get(eventId) ?? null : null;
      return {
        ...(event && typeof event === "object" ? event : {}),
        eventId,
        stored: Boolean(portalEventId),
        portalEventId
      };
    });
    const totalEvents =
      "totalEvents" in payload && typeof payload.totalEvents === "number" ? payload.totalEvents : events.length;

    res.json({
      sourceBaseUrl: resolveSourceBaseUrl(sourceBaseUrl),
      sourceStatus: result.sourceStatus,
      message: result.message,
      totalEvents,
      storedCount: events.filter((event) => event.stored).length,
      missingCount: events.filter((event) => event.eventId && !event.stored).length,
      events
    });
  } catch (error) {
    fail(error, next);
  }
};

export const replaySourceEvent: RequestHandler = async (req, res, next) => {
  try {
    const eventId = req.params.eventId ?? "";
    const correlationId = queryValue(req.query.correlationId);
    const sourceBaseUrl = requestSourceBaseUrl(req);
    const result = await fetchSourceEvent(eventId, correlationId, requestSourceApiKey(req), sourceBaseUrl);
    const stored = findPortalEventsBySourceEventIds([eventId]);
    const portalEventId = stored.get(eventId.trim()) ?? null;
    res.json({
      sourceBaseUrl: resolveSourceBaseUrl(sourceBaseUrl),
      sourceStatus: result.sourceStatus,
      message: result.message,
      eventId: eventId.trim(),
      stored: Boolean(portalEventId),
      portalEventId,
      payload: result.body
    });
  } catch (error) {
    fail(error, next);
  }
};
