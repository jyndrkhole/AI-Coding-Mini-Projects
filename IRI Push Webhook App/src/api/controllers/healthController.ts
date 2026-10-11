import type { RequestHandler } from "express";
import { isPortalAuthEnabled } from "../../config/portalSession.ts";

export const getHealth: RequestHandler = (_req, res) => {
  res.json({
    status: "ok",
    service: "iri-push-notification-test-portal",
    timestamp: new Date().toISOString(),
    portalAuthEnabled: isPortalAuthEnabled()
  });
};
