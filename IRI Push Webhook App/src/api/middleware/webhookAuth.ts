import type { RequestHandler } from "express";
import { getRuntimeConfig } from "../../config/runtimeConfig.ts";

export const webhookAuth: RequestHandler = (req, res, next) => {
  const config = getRuntimeConfig();
  if (!config.authEnabled) {
    next();
    return;
  }

  const expected = process.env.WEBHOOK_API_KEY ?? "";
  const provided = req.header("x-api-key") ?? "";
  if (!expected || provided !== expected) {
    res.status(401).json({
      status: "error",
      message: "Unauthorized"
    });
    return;
  }

  next();
};
