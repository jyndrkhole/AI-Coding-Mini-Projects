import type { RequestHandler } from "express";
import { env } from "../../config/env.ts";
import { getRuntimeConfig, updateRuntimeConfig } from "../../config/runtimeConfig.ts";
import { ALLOWED_RESPONSE_STATUSES } from "../../types/index.ts";

export const getConfig: RequestHandler = (_req, res) => {
  const runtime = getRuntimeConfig();
  res.json({
    ...runtime,
    authEnabled: runtime.authEnabled,
    allowedResponseStatuses: ALLOWED_RESPONSE_STATUSES,
    webhookUrl: `${runtime.publicBaseUrl}${runtime.webhookPath}`,
    catalogVersion: env.iriVersion
  });
};

export const putConfig: RequestHandler = (req, res, next) => {
  try {
    const { responseStatus, responseDelayMs } = req.body ?? {};
    const updated = updateRuntimeConfig({
      responseStatus: responseStatus === undefined ? undefined : Number(responseStatus),
      responseDelayMs: responseDelayMs === undefined ? undefined : Number(responseDelayMs)
    });
    res.json({
      ...updated,
      allowedResponseStatuses: ALLOWED_RESPONSE_STATUSES,
      webhookUrl: `${updated.publicBaseUrl}${updated.webhookPath}`,
      catalogVersion: env.iriVersion
    });
  } catch (error) {
    const err = error as Error & { status?: number };
    err.status = 400;
    next(err);
  }
};
