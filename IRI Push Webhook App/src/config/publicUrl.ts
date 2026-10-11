import type { Request } from "express";
import { env } from "./env.ts";

function firstHeader(req: Request, name: string): string {
  const raw = req.get(name);
  if (!raw) {
    return "";
  }
  return raw.split(",")[0]?.trim() ?? "";
}

function hostnameFromBase(value: string): string {
  try {
    return new URL(value.includes("://") ? value : `http://${value}`).hostname;
  } catch {
    return "";
  }
}

export function isLoopbackBaseUrl(value: string): boolean {
  const hostname = hostnameFromBase(value).toLowerCase();
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

function configuredPublicBaseUrl(): string {
  const fromEnv = process.env.PUBLIC_BASE_URL?.trim() || env.publicBaseUrl;
  return fromEnv.replace(/\/$/, "");
}

function publicBaseUrlFromRequest(req: Request): string {
  const host = firstHeader(req, "x-forwarded-host") || firstHeader(req, "host");
  if (!host) {
    return configuredPublicBaseUrl();
  }
  const proto = firstHeader(req, "x-forwarded-proto") || req.protocol || "http";
  return `${proto}://${host}`.replace(/\/$/, "");
}

export function advertisedPublicBaseUrl(req: Request): string {
  const configured = configuredPublicBaseUrl();
  if (configured && !isLoopbackBaseUrl(configured)) {
    return configured;
  }
  return publicBaseUrlFromRequest(req);
}

export function advertisedWebhookUrl(req: Request, webhookPath: string): string {
  return `${advertisedPublicBaseUrl(req)}${webhookPath}`;
}
