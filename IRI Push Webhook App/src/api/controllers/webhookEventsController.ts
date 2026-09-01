import type { RequestHandler } from "express";
import {
  deleteAllWebhookEvents,
  getWebhookEventById,
  listWebhookEvents
} from "../../repositories/webhookEventRepository.ts";

export const listEvents: RequestHandler = (req, res, next) => {
  try {
    const statusParam = typeof req.query.status === "string" ? Number(req.query.status) : undefined;
    const result = listWebhookEvents({
      eventType: typeof req.query.eventType === "string" ? req.query.eventType : undefined,
      policyNumber: typeof req.query.policyNumber === "string" ? req.query.policyNumber : undefined,
      status: Number.isFinite(statusParam) ? statusParam : undefined,
      from: typeof req.query.from === "string" ? req.query.from : undefined,
      to: typeof req.query.to === "string" ? req.query.to : undefined,
      search: typeof req.query.search === "string" ? req.query.search : undefined,
      limit: typeof req.query.limit === "string" ? Number(req.query.limit) : undefined,
      offset: typeof req.query.offset === "string" ? Number(req.query.offset) : undefined
    });
    res.json(result);
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
