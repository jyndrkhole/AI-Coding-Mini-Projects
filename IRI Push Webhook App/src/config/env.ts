import dotenv from "dotenv";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = path.resolve(__dirname, "../..");

dotenv.config({ path: path.join(PROJECT_ROOT, ".env") });

function envString(name: string, fallback: string): string {
  const value = process.env[name];
  return value === undefined || value === "" ? fallback : value;
}

function envNumber(name: string, fallback: number): number {
  const value = process.env[name];
  if (value === undefined || value === "") {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function envBoolean(name: string, fallback: boolean): boolean {
  const value = process.env[name];
  if (value === undefined || value === "") {
    return fallback;
  }
  return ["1", "true", "yes", "on"].includes(value.toLowerCase());
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
  corsOrigin: envString("CORS_ORIGIN", "*"),
  bodyLimit: envString("BODY_LIMIT", "1mb"),
  rateLimitWindowMs: envNumber("RATE_LIMIT_WINDOW_MS", 60_000),
  rateLimitMax: envNumber("RATE_LIMIT_MAX", 300)
};
