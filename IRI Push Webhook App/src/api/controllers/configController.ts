import type { Request, RequestHandler } from "express";
import { env } from "../../config/env.ts";
import { isPortalAuthEnabled } from "../../config/portalSession.ts";
import { advertisedPublicBaseUrl, advertisedWebhookUrl } from "../../config/publicUrl.ts";
import { getRuntimeConfig, updateRuntimeConfig } from "../../config/runtimeConfig.ts";
import { ALLOWED_RESPONSE_STATUSES } from "../../types/index.ts";

function configPayload(req: Request, runtime = getRuntimeConfig()) {
  const publicBaseUrl = advertisedPublicBaseUrl(req);
  return {
    ...runtime,
    publicBaseUrl,
    authEnabled: runtime.authEnabled,
    allowedResponseStatuses: ALLOWED_RESPONSE_STATUSES,
    webhookUrl: advertisedWebhookUrl(req, runtime.webhookPath),
    catalogVersion: env.iriVersion,
    portalAuthEnabled: isPortalAuthEnabled()
  };
}

export const getConfig: RequestHandler = (req, res) => {
  res.json(configPayload(req));
};

export const putConfig: RequestHandler = (req, res, next) => {
  try {
    const { responseStatus, responseDelayMs } = req.body ?? {};
    const updated = updateRuntimeConfig({
      responseStatus: responseStatus === undefined ? undefined : Number(responseStatus),
      responseDelayMs: responseDelayMs === undefined ? undefined : Number(responseDelayMs)
    });
    res.json(configPayload(req, updated));
  } catch (error) {
    const err = error as Error & { status?: number };
    err.status = 400;
    next(err);
  }
};
