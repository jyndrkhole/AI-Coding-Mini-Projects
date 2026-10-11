import { createHmac, createHash, timingSafeEqual } from "node:crypto";
import type { Request, Response } from "express";
import { env } from "./env.ts";

const LEGACY_PORTAL_COOKIE = "portal_session";
const DEFAULT_SESSION_TTL_MS = 60 * 60 * 1000;

/** Browsers share cookies across ports on the same host, so each app needs its own name. */
export function portalCookieName(): string {
  const custom = process.env.PORTAL_COOKIE_NAME?.trim();
  if (custom && /^[A-Za-z0-9_-]+$/.test(custom)) {
    return custom;
  }
  return `portal_session_${env.port}`;
}

/**
 * Portal cookie lifetime.
 * Prefer PORTAL_SESSION_TTL_MINUTES for short local tests (e.g. 1).
 * Otherwise PORTAL_SESSION_TTL_HOURS (default 1 hour).
 */
export function portalSessionTtlMs(): number {
  const minutesRaw = process.env.PORTAL_SESSION_TTL_MINUTES?.trim();
  if (minutesRaw) {
    const minutes = Number(minutesRaw);
    if (Number.isFinite(minutes) && minutes > 0 && minutes <= 60 * 24 * 7) {
      return Math.floor(minutes * 60 * 1000);
    }
  }
  const hoursRaw = process.env.PORTAL_SESSION_TTL_HOURS?.trim();
  if (hoursRaw) {
    const hours = Number(hoursRaw);
    if (Number.isFinite(hours) && hours > 0 && hours <= 168) {
      return Math.floor(hours * 60 * 60 * 1000);
    }
  }
  return DEFAULT_SESSION_TTL_MS;
}

function envFlag(name: string, fallback: boolean): boolean {
  const value = process.env[name];
  if (value === undefined || value === "") {
    return fallback;
  }
  return ["1", "true", "yes", "on"].includes(value.trim().toLowerCase());
}

export function isPortalAuthEnabled(): boolean {
  const raw = process.env.PORTAL_AUTH_ENABLED;
  if (raw !== undefined && raw.trim() !== "") {
    return ["1", "true", "yes", "on"].includes(raw.trim().toLowerCase());
  }
  if (env.portalAuthEnabled) {
    return true;
  }
  return env.nodeEnv === "production";
}

export function portalUsername(): string {
  return (process.env.PORTAL_USERNAME || env.portalUsername || "admin").trim() || "admin";
}

export function portalPassword(): string {
  return (process.env.PORTAL_PASSWORD ?? env.portalPassword).trim().replace(/^['"]|['"]$/g, "");
}

function safeEqual(left: string, right: string): boolean {
  const a = createHash("sha256").update(left).digest();
  const b = createHash("sha256").update(right).digest();
  return timingSafeEqual(a, b);
}

export function credentialsMatch(username: string, password: string): boolean {
  const expectedUser = portalUsername();
  const expectedPass = portalPassword();
  if (!expectedPass) {
    return false;
  }
  return safeEqual(username, expectedUser) && safeEqual(password, expectedPass);
}

function sessionSecret(): Buffer {
  return createHash("sha256").update(`portal-session:${portalCookieName()}:${portalPassword()}`).digest();
}

export function signPortalSession(username: string, now = Date.now()): string {
  const exp = String(now + portalSessionTtlMs());
  const payload = `${exp}.${username}`;
  const mac = createHmac("sha256", sessionSecret()).update(payload).digest("hex");
  return `${payload}.${mac}`;
}

export function readCookie(req: Request, name: string): string {
  const header = req.get("cookie") ?? "";
  for (const part of header.split(";")) {
    const trimmed = part.trim();
    const eq = trimmed.indexOf("=");
    if (eq <= 0) {
      continue;
    }
    if (trimmed.slice(0, eq) === name) {
      try {
        return decodeURIComponent(trimmed.slice(eq + 1));
      } catch {
        return "";
      }
    }
  }
  return "";
}

export function verifyPortalSession(token: string): string | null {
  const parts = token.split(".");
  if (parts.length < 3) {
    return null;
  }
  const mac = parts.pop() as string;
  const username = parts.pop() as string;
  const exp = parts.join(".");
  if (!exp || !username || !mac || !portalPassword()) {
    return null;
  }
  const payload = `${exp}.${username}`;
  const expected = createHmac("sha256", sessionSecret()).update(payload).digest("hex");
  if (!safeEqual(mac, expected)) {
    return null;
  }
  const expiresAt = Number(exp);
  if (!Number.isFinite(expiresAt) || expiresAt < Date.now()) {
    return null;
  }
  return username;
}

export function sessionUsername(req: Request): string | null {
  const token = readCookie(req, portalCookieName());
  if (!token) {
    return null;
  }
  return verifyPortalSession(token);
}

function cookieHeader(name: string, value: string, maxAge: number, secure: boolean): string {
  const parts = [
    `${name}=${value}`,
    "Path=/",
    "HttpOnly",
    "SameSite=Lax",
    `Max-Age=${maxAge}`
  ];
  if (secure) {
    parts.push("Secure");
  }
  return parts.join("; ");
}

export function setPortalCookie(req: Request, res: Response, username: string): void {
  const forwarded = req.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const secure = (forwarded || req.protocol) === "https";
  const token = signPortalSession(username);
  const maxAge = Math.floor(portalSessionTtlMs() / 1000);
  const cookies = [cookieHeader(portalCookieName(), encodeURIComponent(token), maxAge, secure)];
  if (portalCookieName() !== LEGACY_PORTAL_COOKIE) {
    cookies.push(cookieHeader(LEGACY_PORTAL_COOKIE, "", 0, secure));
  }
  res.setHeader("Set-Cookie", cookies);
}

export function clearPortalCookie(res: Response): void {
  const cookies = [cookieHeader(portalCookieName(), "", 0, false)];
  if (portalCookieName() !== LEGACY_PORTAL_COOKIE) {
    cookies.push(cookieHeader(LEGACY_PORTAL_COOKIE, "", 0, false));
  }
  res.setHeader("Set-Cookie", cookies);
}
