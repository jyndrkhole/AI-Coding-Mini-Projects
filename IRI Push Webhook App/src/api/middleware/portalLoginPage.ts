import type { RequestHandler } from "express";
import { isPortalAuthEnabled, sessionUsername } from "../../config/portalSession.ts";
import { renderPortalLoginPage } from "../../views/portalLoginPage.ts";

const OPEN_PREFIXES = ["/api", "/webhooks", "/health", "/api-docs"];

export const servePortalLoginPage: RequestHandler = (req, res, next) => {
  if (!isPortalAuthEnabled() || sessionUsername(req)) {
    next();
    return;
  }
  if (OPEN_PREFIXES.some((prefix) => req.path === prefix || req.path.startsWith(`${prefix}/`))) {
    next();
    return;
  }
  if (req.method !== "GET" && req.method !== "HEAD") {
    next();
    return;
  }
  if (/\.[a-z0-9]+$/i.test(req.path) && !req.path.endsWith(".html")) {
    next();
    return;
  }
  res.setHeader("Cache-Control", "no-store");
  res.status(200).type("html").send(renderPortalLoginPage());
};
