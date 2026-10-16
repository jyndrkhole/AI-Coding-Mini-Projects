import { env } from "../config/env.ts";

const AUTH_PATH = "/getAuthToken";
const RECONCILIATION_PATH = "/v1/application-notifications/reconciliation";
const EVENT_PATH = "/v1/application-notifications";
const TOKEN_FIELDS = ["token", "accessToken", "access_token", "authToken", "jwt", "id_token", "idToken"];

interface CachedToken {
  key: string;
  token: string;
  expiresAt: number;
}

let cachedToken: CachedToken | null = null;

export function clearSourceAuthCache(): void {
  cachedToken = null;
}

export class SourceApiError extends Error {
  status: number;
  constructor(message: string, status = 400) {
    super(message);
    this.status = status;
  }
}

export interface SourceCallResult {
  sourceStatus: number;
  body: unknown;
  message: string;
}

const PORTAL_ENVIRONMENTS = ["QA", "INT", "PROD"] as const;
export type PortalEnvironment = (typeof PORTAL_ENVIRONMENTS)[number];

function configuredValue(name: string, fallback = ""): string {
  const fromProcess = process.env[name];
  return (fromProcess !== undefined ? fromProcess : fallback).trim();
}

export function portalEnvironment(): PortalEnvironment | "" {
  const value = configuredValue("PORTAL_ENVIRONMENT", env.portalEnvironment).toUpperCase();
  return PORTAL_ENVIRONMENTS.includes(value as PortalEnvironment) ? (value as PortalEnvironment) : "";
}

export function sourceApiBaseUrl(): string {
  const explicit = configuredValue("SOURCE_API_BASE_URL", env.sourceApiBaseUrl).replace(/\/$/, "");
  if (explicit) {
    return explicit;
  }
  const environment = portalEnvironment();
  if (environment === "QA") {
    return configuredValue("SOURCE_API_BASE_URL_QA", env.sourceApiBaseUrlQa).replace(/\/$/, "");
  }
  if (environment === "INT") {
    return configuredValue("SOURCE_API_BASE_URL_INT", env.sourceApiBaseUrlInt).replace(/\/$/, "");
  }
  if (environment === "PROD") {
    return configuredValue("SOURCE_API_BASE_URL_PROD", env.sourceApiBaseUrlProd).replace(/\/$/, "");
  }
  return "";
}

export function missingSourceUrlMessage(): string {
  const rawEnvironment = configuredValue("PORTAL_ENVIRONMENT", env.portalEnvironment);
  const environment = portalEnvironment();
  if (rawEnvironment && !environment) {
    return "PORTAL_ENVIRONMENT must be QA, INT, or PROD.";
  }
  if (environment) {
    return `SOURCE_API_BASE_URL_${environment} is not set. Add the ${environment} source URL and restart the portal.`;
  }
  return "Set PORTAL_ENVIRONMENT to QA, INT, or PROD and the matching SOURCE_API_BASE_URL_QA, SOURCE_API_BASE_URL_INT, or SOURCE_API_BASE_URL_PROD.";
}

export function normalizeSourceBase(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return trimmed.replace(/\/$/, "");
  }
  parsed.search = "";
  parsed.hash = "";
  const path = parsed.pathname
    .replace(/\/+$/, "")
    .replace(/\/v1\/application-notifications(?:\/.*)?$/i, "")
    .replace(/\/getAuthToken$/i, "");
  parsed.pathname = path || "/";
  return parsed.toString().replace(/\/$/, "");
}

export function resolveSourceBaseUrl(override?: string): string {
  const supplied = normalizeSourceBase(override ?? "");
  return supplied || normalizeSourceBase(sourceApiBaseUrl());
}

export function sourceApiKey(override?: string): string {
  const supplied = override?.trim() ?? "";
  if (supplied) {
    return supplied;
  }
  return configuredValue("SOURCE_X_API_KEY", "") || configuredValue("SOURCE_API_KEY", env.sourceApiKey);
}

function sourceOrigin(override?: string): URL {
  const base = resolveSourceBaseUrl(override);
  if (!base) {
    throw new SourceApiError(missingSourceUrlMessage());
  }
  let parsed: URL;
  try {
    parsed = new URL(base);
  } catch {
    throw new SourceApiError("Source endpoint must be an http:// or https:// URL.");
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new SourceApiError("Source endpoint must be an http:// or https:// URL.");
  }
  if (parsed.username || parsed.password) {
    throw new SourceApiError("Source endpoint must not include a username or password.");
  }
  if (!parsed.pathname.endsWith("/")) {
    parsed.pathname = `${parsed.pathname}/`;
  }
  return parsed;
}

function readBody(text: string): unknown {
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function messageFrom(body: unknown, status: number): string {
  if (body && typeof body === "object" && "message" in body && typeof body.message === "string") {
    return body.message;
  }
  return status >= 200 && status < 300 ? "" : `Source API returned ${status}`;
}

function tokenFrom(body: unknown): string {
  if (typeof body === "string") {
    const value = body.trim().replace(/^Bearer\s+/i, "");
    return value.startsWith("eyJ") || value.length > 20 ? value : "";
  }
  if (!body || typeof body !== "object") {
    return "";
  }
  const record = body as Record<string, unknown>;
  for (const field of TOKEN_FIELDS) {
    const value = record[field];
    if (typeof value === "string" && value.trim()) {
      return value.trim().replace(/^Bearer\s+/i, "");
    }
  }
  if (record.data && typeof record.data === "object") {
    return tokenFrom(record.data);
  }
  return "";
}

function tokenExpiry(token: string): number {
  const payload = token.split(".")[1];
  if (!payload) {
    return Date.now() + 10 * 60 * 1000;
  }
  try {
    const json = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as { exp?: unknown };
    if (typeof json.exp === "number" && Number.isFinite(json.exp)) {
      return json.exp * 1000;
    }
  } catch {
    // A non-JWT token is cached briefly and refreshed on 401.
  }
  return Date.now() + 10 * 60 * 1000;
}

async function fetchSourceToken(base: URL, sourceKey?: string): Promise<string> {
  const apiKey = sourceApiKey(sourceKey);
  if (!apiKey) {
    throw new SourceApiError(
      "Enter the source x-api-key, or set SOURCE_API_KEY for this environment. It is sent as x-api-key to getAuthToken."
    );
  }
  const key = `${base.origin}${base.pathname}|${apiKey}`;
  if (cachedToken && cachedToken.key === key && cachedToken.expiresAt > Date.now() + 30_000) {
    return cachedToken.token;
  }

  const url = new URL(AUTH_PATH.replace(/^\//, ""), base);
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { Accept: "application/json", "x-api-key": apiKey },
      signal: AbortSignal.timeout(20_000)
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : "request failed";
    throw new SourceApiError(`Could not reach the source API at ${url.origin}: ${reason}`, 502);
  }
  const text = await response.text();
  const body = readBody(text);
  if (!response.ok) {
    throw new SourceApiError(
      `Source getAuthToken failed (${response.status}): ${messageFrom(body, response.status)}`,
      502
    );
  }
  const token = tokenFrom(body);
  if (!token) {
    throw new SourceApiError(
      "Source getAuthToken did not return a token. Expected token, accessToken, or access_token.",
      502
    );
  }
  cachedToken = { key, token, expiresAt: tokenExpiry(token) };
  return token;
}

async function callSource(
  url: URL,
  origin: URL,
  correlationId?: string,
  allowRetry = true,
  sourceKey?: string
): Promise<SourceCallResult> {
  const token = await fetchSourceToken(origin, sourceKey);
  const headers: Record<string, string> = { Accept: "application/json", Authorization: token };
  const correlation = correlationId?.trim();
  if (correlation) {
    headers.correlationId = correlation;
  }
  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers,
      signal: AbortSignal.timeout(20_000)
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : "request failed";
    throw new SourceApiError(`Could not reach the source API at ${url.origin}: ${reason}`, 502);
  }
  if (response.status === 401 && allowRetry) {
    cachedToken = null;
    await response.body?.cancel().catch(() => undefined);
    return callSource(url, origin, correlationId, false, sourceKey);
  }
  const text = await response.text();
  const body = readBody(text);
  const parsed = typeof body === "string" ? { raw: body } : body;
  return { sourceStatus: response.status, body: parsed, message: messageFrom(body, response.status) };
}

export function fetchReconciliation(input: {
  startTime: string;
  endTime: string;
  associatedFirmId?: string;
  correlationId?: string;
  sourceApiKey?: string;
  sourceBaseUrl?: string;
}): Promise<SourceCallResult> {
  const origin = sourceOrigin(input.sourceBaseUrl);
  const url = new URL(RECONCILIATION_PATH.replace(/^\//, ""), origin);
  url.searchParams.set("startTime", input.startTime);
  url.searchParams.set("endTime", input.endTime);
  const firmId = input.associatedFirmId?.trim();
  if (firmId) {
    url.searchParams.set("associatedFirmId", firmId);
  }
  return callSource(url, origin, input.correlationId, true, input.sourceApiKey);
}

export function fetchSourceEvent(
  eventId: string,
  correlationId?: string,
  sourceKey?: string,
  sourceBaseUrl?: string
): Promise<SourceCallResult> {
  const id = eventId.trim();
  if (!id || id.includes("/") || id.includes("\\")) {
    throw new SourceApiError("eventId is required.");
  }
  const origin = sourceOrigin(sourceBaseUrl);
  const url = new URL(`${EVENT_PATH.replace(/^\//, "")}/${encodeURIComponent(id)}`, origin);
  return callSource(url, origin, correlationId, true, sourceKey);
}
