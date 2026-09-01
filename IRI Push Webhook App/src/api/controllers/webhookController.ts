import type { RequestHandler } from "express";
import { processWebhook, sourceIpFromRequest } from "../../services/webhookService.ts";

export const receiveWebhook: RequestHandler = async (req, res, next) => {
  try {
    const result = await processWebhook({
      method: req.method,
      path: req.originalUrl.split("?")[0] ?? req.path,
      headers: req.headers,
      body: req.body,
      rawBody: req.rawBody,
      jsonParseError: req.jsonParseError,
      sourceIp: sourceIpFromRequest(req)
    });
    res.status(result.status).json(result.body);
  } catch (error) {
    next(error);
  }
};
