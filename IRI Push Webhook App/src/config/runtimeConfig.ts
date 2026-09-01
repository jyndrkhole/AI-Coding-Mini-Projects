import { ALLOWED_RESPONSE_STATUSES, type RuntimeConfig } from "../types/index.ts";
import { env } from "./env.ts";

const state: RuntimeConfig = {
  responseStatus: env.webhookResponseStatus,
  responseDelayMs: env.webhookResponseDelayMs,
  authEnabled: env.webhookAuthEnabled,
  iriVersion: env.iriVersion,
  webhookPath: "/webhooks/iri",
  publicBaseUrl: env.publicBaseUrl.replace(/\/$/, "")
};

export function getRuntimeConfig(): RuntimeConfig {
  return { ...state };
}

export function updateRuntimeConfig(patch: Partial<Pick<RuntimeConfig, "responseStatus" | "responseDelayMs">>): RuntimeConfig {
  if (patch.responseStatus !== undefined) {
    if (!ALLOWED_RESPONSE_STATUSES.includes(patch.responseStatus as (typeof ALLOWED_RESPONSE_STATUSES)[number])) {
      throw new Error(`Unsupported response status ${patch.responseStatus}`);
    }
    state.responseStatus = patch.responseStatus;
  }
  if (patch.responseDelayMs !== undefined) {
    if (!Number.isFinite(patch.responseDelayMs) || patch.responseDelayMs < 0 || patch.responseDelayMs > 60_000) {
      throw new Error("responseDelayMs must be between 0 and 60000");
    }
    state.responseDelayMs = Math.round(patch.responseDelayMs);
  }
  return getRuntimeConfig();
}

export function resetRuntimeConfig(): RuntimeConfig {
  state.responseStatus = env.webhookResponseStatus;
  state.responseDelayMs = env.webhookResponseDelayMs;
  state.authEnabled = env.webhookAuthEnabled;
  state.iriVersion = env.iriVersion;
  state.publicBaseUrl = env.publicBaseUrl.replace(/\/$/, "");
  return getRuntimeConfig();
}

export function setAuthEnabledForTests(enabled: boolean): void {
  state.authEnabled = enabled;
}
