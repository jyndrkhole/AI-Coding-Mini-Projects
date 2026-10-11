import type { RequestHandler } from "express";
import rateLimit from "express-rate-limit";
import { env } from "../../config/env.ts";
import { renderPortalLoginPage } from "../../views/portalLoginPage.ts";
import {
  clearPortalCookie,
  credentialsMatch,
  isPortalAuthEnabled,
  portalPassword,
  portalUsername,
  sessionUsername,
  setPortalCookie
} from "../../config/portalSession.ts";

function isFormPost(req: { is: (type: string) => string | false | null }): boolean {
  return Boolean(req.is("application/x-www-form-urlencoded"));
}

export const portalLoginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 20,
  standardHeaders: true,
  legacyHeaders: false,
  skip: () => env.nodeEnv === "test",
  validate: { xForwardedForHeader: false },
  message: {
    status: "error",
    message: "Too many login attempts. Try again later."
  }
});

export const getPortalSession: RequestHandler = (req, res) => {
  const enabled = isPortalAuthEnabled();
  const username = sessionUsername(req);
  res.json({
    enabled,
    authenticated: !enabled || Boolean(username),
    username: username ?? null
  });
};

export const portalLogin: RequestHandler = (req, res) => {
  const form = isFormPost(req);
  if (!isPortalAuthEnabled()) {
    if (form) {
      res.redirect(303, "/");
      return;
    }
    res.json({ enabled: false, authenticated: true, username: null });
    return;
  }
  if (!portalPassword()) {
    const message = "Portal login is enabled but PORTAL_PASSWORD is not set";
    if (form) {
      res.status(503).type("html").send(renderPortalLoginPage(message));
      return;
    }
    res.status(503).json({
      status: "error",
      message
    });
    return;
  }
  const username = typeof req.body?.username === "string" ? req.body.username : "";
  const password = typeof req.body?.password === "string" ? req.body.password : "";
  if (!credentialsMatch(username, password)) {
    const message = "Invalid username or password";
    if (form) {
      res.status(401).type("html").send(renderPortalLoginPage(message));
      return;
    }
    res.status(401).json({
      status: "error",
      message
    });
    return;
  }
  setPortalCookie(req, res, portalUsername());
  if (form) {
    res.redirect(303, "/");
    return;
  }
  res.json({
    enabled: true,
    authenticated: true,
    username: portalUsername()
  });
};

export const portalLogout: RequestHandler = (_req, res) => {
  clearPortalCookie(res);
  res.json({ enabled: isPortalAuthEnabled(), authenticated: false, username: null });
};
