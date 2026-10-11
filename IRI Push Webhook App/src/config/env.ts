import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = path.resolve(__dirname, "../..");

function decodeEnvBuffer(buf: Buffer): string {
  if (buf.length >= 2 && buf[0] === 0xff && buf[1] === 0xfe) {
    return buf.subarray(2).toString("utf16le");
  }
  if (buf.length >= 2 && buf[0] === 0xfe && buf[1] === 0xff) {
    const swapped = Buffer.alloc(buf.length - 2);
    for (let i = 2; i + 1 < buf.length; i += 2) {
      swapped[i - 2] = buf[i + 1];
      swapped[i - 1] = buf[i];
    }
    return swapped.toString("utf16le");
  }
  let start = 0;
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) {
    start = 3;
  }
  return buf.subarray(start).toString("utf8");
}

function applyEnvLine(line: string): void {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) {
    return;
  }
  const eq = trimmed.indexOf("=");
  if (eq <= 0) {
    return;
  }
  const key = trimmed.slice(0, eq).trim().replace(/^\uFEFF/, "");
  let value = trimmed.slice(eq + 1).trim();
  if (
    (value.startsWith("\"") && value.endsWith("\"")) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  const current = process.env[key];
  if (current === undefined || current === "") {
    process.env[key] = value;
  }
}

export function loadEnvFiles(): string[] {
  const loaded: string[] = [];
  const candidates = [
    path.join(PROJECT_ROOT, ".env"),
    path.join(process.cwd(), ".env")
  ];
  for (const filePath of candidates) {
    if (!fs.existsSync(filePath)) {
      continue;
    }
    try {
      const text = decodeEnvBuffer(fs.readFileSync(filePath));
      for (const line of text.split(/\r?\n/)) {
        applyEnvLine(line);
      }
      loaded.push(filePath);
    } catch {
      /* ignore unreadable env files */
    }
  }
  return loaded;
}

export const loadedEnvFiles = loadEnvFiles();

function envString(name: string, fallback: string): string {
  const value = process.env[name];
  if (value === undefined || value === "") {
    return fallback;
  }
  return value.trim().replace(/^['"]|['"]$/g, "");
}

function envNumber(name: string, fallback: number): number {
  const value = process.env[name];
  if (value === undefined || value === "") {
    return fallback;
  }
  const parsed = Number(value.trim());
  return Number.isFinite(parsed) ? parsed : fallback;
}

function envBoolean(name: string, fallback: boolean): boolean {
  const value = process.env[name];
  if (value === undefined || value === "") {
    return fallback;
  }
  return ["1", "true", "yes", "on"].includes(value.trim().toLowerCase());
}

export const env = {
  port: envNumber("PORT", 3000),
  nodeEnv: envString("NODE_ENV", "development"),
  publicBaseUrl: envString("PUBLIC_BASE_URL", "http://localhost:3000"),
  databasePath: envString("DATABASE_PATH", "./data/webhook-events.db"),
  iriVersion: envString("IRI_VERSION", "v1"),
  webhookResponseStatus: envNumber("WEBHOOK_RESPONSE_STATUS", 200),
  webhookResponseDelayMs: envNumber("WEBHOOK_RESPONSE_DELAY_MS", 0),
  webhookAuthEnabled: envBoolean("WEBHOOK_AUTH_ENABLED", false),
  webhookApiKey: envString("WEBHOOK_API_KEY", ""),
  portalAuthEnabled: envBoolean("PORTAL_AUTH_ENABLED", false),
  portalUsername: envString("PORTAL_USERNAME", "admin"),
  portalPassword: envString("PORTAL_PASSWORD", ""),
  corsOrigin: envString("CORS_ORIGIN", "*"),
  bodyLimit: envString("BODY_LIMIT", "1mb"),
  rateLimitWindowMs: envNumber("RATE_LIMIT_WINDOW_MS", 60_000),
  rateLimitMax: envNumber("RATE_LIMIT_MAX", 300)
};
