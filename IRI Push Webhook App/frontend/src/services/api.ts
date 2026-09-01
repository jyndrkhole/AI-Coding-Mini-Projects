import type {
  CatalogEvent,
  DashboardStats,
  EventCatalog,
  EventListQuery,
  EventListResult,
  PortalConfig,
  WebhookEvent
} from "../types";

async function parseJson<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.message || `Request failed (${response.status})`);
  }
  return payload as T;
}

function queryString(query: EventListQuery): string {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  getStats: () => fetch("/api/stats").then((res) => parseJson<DashboardStats>(res)),
  getConfig: () => fetch("/api/config").then((res) => parseJson<PortalConfig>(res)),
  updateConfig: (body: { responseStatus?: number; responseDelayMs?: number }) =>
    fetch("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then((res) => parseJson<PortalConfig>(res)),
  getCatalog: () => fetch("/api/events").then((res) => parseJson<EventCatalog>(res)),
  getCatalogEvent: (eventType: string) =>
    fetch(`/api/events/${encodeURIComponent(eventType)}`).then((res) => parseJson<CatalogEvent>(res)),
  listWebhookEvents: (query: EventListQuery = {}) =>
    fetch(`/api/webhook-events${queryString(query)}`).then((res) => parseJson<EventListResult>(res)),
  getWebhookEvent: (id: string) =>
    fetch(`/api/webhook-events/${id}`).then((res) => parseJson<WebhookEvent>(res)),
  clearWebhookEvents: () =>
    fetch("/api/webhook-events", { method: "DELETE" }).then((res) => parseJson<{ deleted: number }>(res)),
  getHealth: () =>
    fetch("/health").then((res) => parseJson<{ status: string; service: string; timestamp: string }>(res)),
  sendWebhook: (payload: unknown, apiKey?: string) => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }
    return fetch("/webhooks/iri", {
      method: "POST",
      headers,
      body: JSON.stringify(payload)
    }).then(async (res) => {
      const body = await res.json().catch(() => ({}));
      return { status: res.status, body };
    });
  }
};
