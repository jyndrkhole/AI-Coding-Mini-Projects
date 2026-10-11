import type { PortalConfig } from "../types";

const DEFAULT_PATH = "/webhooks/iri";

function isLoopbackBaseUrl(value: string): boolean {
  try {
    const hostname = new URL(value.includes("://") ? value : `http://${value}`).hostname.toLowerCase();
    return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
  } catch {
    return true;
  }
}

export function advertisedWebhookUrl(config?: PortalConfig | null): string {
  const path = config?.webhookPath ?? DEFAULT_PATH;
  const configured = config?.publicBaseUrl?.replace(/\/$/, "") ?? "";
  if (configured && !isLoopbackBaseUrl(configured)) {
    return `${configured}${path}`;
  }
  const origin = window.location.origin.replace(/\/$/, "");
  return `${origin}${path}`;
}
