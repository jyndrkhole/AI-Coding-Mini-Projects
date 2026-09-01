import type { RequestHandler } from "express";

export const getHealth: RequestHandler = (_req, res) => {
  res.json({
    status: "ok",
    service: "iri-push-notification-test-portal",
    timestamp: new Date().toISOString()
  });
};
