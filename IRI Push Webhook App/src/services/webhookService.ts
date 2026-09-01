import { randomUUID } from "node:crypto";
import type { Request } from "express";
import { getRuntimeConfig } from "../config/runtimeConfig.ts";
import { insertWebhookEvent } from "../repositories/webhookEventRepository.ts";
import { broadcastWebhookEvent } from "./sseService.ts";
import { maskHeaders } from "../utils/maskHeaders.ts";
import { sleep } from "../utils/sleep.ts";
import type { WebhookEvent } from "../types/index.ts";

export interface IncomingWebhookRequest {
  method: string;
  path: string;
  headers: Record<string, unknown>;
  body: unknown;
  rawBody?: string;
  jsonParseError?: boolean;
  sourceIp?: string | null;
}

function extractEventType(payload: unknown): string | null {
  if (payload && typeof payload === "object" && "eventType" in payload) {
    const value = (payload as { eventType?: unknown }).eventType;
    return typeof value === "string" && value.length > 0 ? value : null;
  }
  return null;
}

function extractPolicyNumber(payload: unknown): string | null {
  if (payload && typeof payload === "object" && "policyNumber" in payload) {
    const value = (payload as { policyNumber?: unknown }).policyNumber;
    return typeof value === "string" && value.length > 0 ? value : null;
  }
  return null;
}

function successBody(eventId: string) {
  return {
    status: "received",
    message: "Webhook received successfully",
    eventId
  };
}

function simulatedErrorBody(eventId: string, status: number) {
  return {
    status: "error",
    message: `Simulated webhook failure (${status})`,
    eventId
  };
}

function invalidJsonBody() {
  return {
    status: "error",
    message: "Invalid JSON payload"
  };
}

export async function processWebhook(input: IncomingWebhookRequest): Promise<{
  status: number;
  body: Record<string, unknown>;
  event: WebhookEvent;
}> {
  const started = Date.now();
  const config = getRuntimeConfig();
  const receivedAt = new Date().toISOString();

  if (input.jsonParseError) {
    const event = insertWebhookEvent({
      eventType: null,
      policyNumber: null,
      receivedAt,
      requestMethod: input.method,
      requestPath: input.path,
      headers: maskHeaders(input.headers),
      payload: { raw: input.rawBody ?? "", parseError: true },
      sourceIp: input.sourceIp ?? null,
      responseStatus: 400,
      responseBody: invalidJsonBody(),
      processingTimeMs: Date.now() - started
    });
    broadcastWebhookEvent(event);
    return { status: 400, body: invalidJsonBody(), event };
  }

  await sleep(config.responseDelayMs);

  const payload = input.body;
  const eventType = extractEventType(payload);
  const policyNumber = extractPolicyNumber(payload);
  const eventId = randomUUID();
  const isSuccess = config.responseStatus >= 200 && config.responseStatus < 300;
  const responseBody = isSuccess
    ? successBody(eventId)
    : simulatedErrorBody(eventId, config.responseStatus);

  const event = insertWebhookEvent({
    id: eventId,
    eventType,
    policyNumber,
    receivedAt,
    requestMethod: input.method,
    requestPath: input.path,
    headers: maskHeaders(input.headers),
    payload,
    sourceIp: input.sourceIp ?? null,
    responseStatus: config.responseStatus,
    responseBody,
    processingTimeMs: Date.now() - started
  });

  broadcastWebhookEvent(event);
  return { status: config.responseStatus, body: responseBody, event };
}

export function sourceIpFromRequest(req: Request): string | null {
  const forwarded = req.headers["x-forwarded-for"];
  if (typeof forwarded === "string" && forwarded.length > 0) {
    return forwarded.split(",")[0]?.trim() ?? null;
  }
  return req.ip ?? req.socket.remoteAddress ?? null;
}
