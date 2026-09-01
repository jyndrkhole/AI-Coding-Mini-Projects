import type { RequestHandler } from "express";
import { findCatalogEvent, loadCatalog } from "../../config/eventsCatalog.ts";
import { env } from "../../config/env.ts";

export const listCatalog: RequestHandler = (_req, res, next) => {
  try {
    res.json(loadCatalog(env.iriVersion));
  } catch (error) {
    next(error);
  }
};

export const getCatalogEvent: RequestHandler = (req, res, next) => {
  try {
    const eventType = req.params.eventType ?? "";
    const event = findCatalogEvent(eventType);
    if (!event) {
      res.status(404).json({ status: "error", message: "Catalog event not found" });
      return;
    }
    res.json(event);
  } catch (error) {
    next(error);
  }
};
