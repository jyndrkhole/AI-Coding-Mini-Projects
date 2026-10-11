import type { RequestHandler } from "express";
import { isPortalAuthEnabled, sessionUsername } from "../../config/portalSession.ts";

export const requirePortalAuth: RequestHandler = (req, res, next) => {
  if (!isPortalAuthEnabled()) {
    next();
    return;
  }
  const username = sessionUsername(req);
  if (!username) {
    res.status(401).json({
      status: "error",
      message: "Portal login required"
    });
    return;
  }
  req.portalUser = username;
  next();
};
