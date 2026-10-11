import type { Request, RequestHandler } from "express";
import {
  deleteAllWebhookEvents,
  getWebhookEventById,
  listWebhookEvents
} from "../../repositories/webhookEventRepository.ts";
import type { EventListFilters, WebhookEvent } from "../../types/index.ts";
import { toCsv } from "../../utils/csv.ts";

const EXPORT_LIMIT = 5000;

function filtersFromQuery(req: Request, includePaging: boolean): EventListFilters {
  const statusParam = typeof req.query.status === "string" ? Number(req.query.status) : undefined;
  const filters: EventListFilters = {
    eventType: typeof req.query.eventType === "string" ? req.query.eventType : undefined,
    policyNumber: typeof req.query.policyNumber === "string" ? req.query.policyNumber : undefined,
    status: Number.isFinite(statusParam) ? statusParam : undefined,
    from: typeof req.query.from === "string" ? req.query.from : undefined,
    to: typeof req.query.to === "string" ? req.query.to : undefined,
    search: typeof req.query.search === "string" ? req.query.search : undefined
  };
  if (includePaging) {
    filters.limit = typeof req.query.limit === "string" ? Number(req.query.limit) : undefined;
    filters.offset = typeof req.query.offset === "string" ? Number(req.query.offset) : undefined;
  }
  return filters;
}

function csvRows(events: WebhookEvent[]): unknown[][] {
  return events.map((event) => [
    event.id,
    event.receivedAt,
    event.eventType,
    event.displayName,
    event.knownEvent,
    event.policyNumber,
    event.responseStatus,
    event.processingTimeMs,
    event.sourceIp,
    event.requestMethod,
    event.requestPath,
    JSON.stringify(event.payload)
  ]);
}

export const listEvents: RequestHandler = (req, res, next) => {
  try {
    const result = listWebhookEvents(filtersFromQuery(req, true));
    res.json(result);
  } catch (error) {
    next(error);
  }
};

export const exportEvents: RequestHandler = (req, res, next) => {
  try {
    const format = typeof req.query.format === "string" ? req.query.format : "json";
    if (format !== "json" && format !== "csv") {
      res.status(400).json({ status: "error", message: "format must be json or csv" });
      return;
    }

    const result = listWebhookEvents(
      { ...filtersFromQuery(req, false), limit: EXPORT_LIMIT, offset: 0 },
      { maxLimit: EXPORT_LIMIT, defaultLimit: EXPORT_LIMIT }
    );
    const truncated = result.total > result.events.length;
    const stamp = new Date().toISOString().slice(0, 10);
    res.setHeader("X-Export-Total", String(result.total));
    res.setHeader("X-Export-Count", String(result.events.length));
    if (truncated) {
      res.setHeader("X-Export-Truncated", "true");
    }

    if (format === "csv") {
      const csv = toCsv(
        [
          "id",
          "receivedAt",
          "eventType",
          "displayName",
          "knownEvent",
          "policyNumber",
          "responseStatus",
          "processingTimeMs",
          "sourceIp",
          "requestMethod",
          "requestPath",
          "payload"
        ],
        csvRows(result.events)
      );
      res.setHeader("Content-Type", "text/csv; charset=utf-8");
      res.setHeader("Content-Disposition", `attachment; filename="webhook-events-${stamp}.csv"`);
      res.send(csv);
      return;
    }

    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.setHeader("Content-Disposition", `attachment; filename="webhook-events-${stamp}.json"`);
    res.send(
      JSON.stringify(
        {
          exportedAt: new Date().toISOString(),
          total: result.total,
          count: result.events.length,
          truncated,
          events: result.events
        },
        null,
        2
      )
    );
  } catch (error) {
    next(error);
  }
};

export const getEvent: RequestHandler = (req, res, next) => {
  try {
    const event = getWebhookEventById(req.params.id ?? "");
    if (!event) {
      res.status(404).json({ status: "error", message: "Webhook event not found" });
      return;
    }
    res.json(event);
  } catch (error) {
    next(error);
  }
};

export const clearEvents: RequestHandler = (_req, res, next) => {
  try {
    const deleted = deleteAllWebhookEvents();
    res.json({ status: "deleted", deleted });
  } catch (error) {
    next(error);
  }
};
