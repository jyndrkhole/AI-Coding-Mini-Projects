import type {
  CatalogEvent,
  DashboardStats,
  EventCatalog,
  EventListQuery,
  EventListResult,
  PortalConfig,
  PortalSession,
  WebhookEvent
} from "../types";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const PORTAL_AUTH_LOST = "portal-auth-lost";

/** Notify the app shell when a protected API call gets 401 (expired/missing session). */
export function onPortalAuthLost(handler: () => void): () => void {
  const listener = () => handler();
  window.addEventListener(PORTAL_AUTH_LOST, listener);
  return () => window.removeEventListener(PORTAL_AUTH_LOST, listener);
}

function notifyPortalAuthLost(): void {
  window.dispatchEvent(new Event(PORTAL_AUTH_LOST));
}

async function parseJson<T>(response: Response, options: { notifyAuthLost?: boolean } = {}): Promise<T> {
  const notifyAuthLost = options.notifyAuthLost !== false;
  const payload = await response.json().catch(() => ({}));
  if (response.status === 401) {
    if (notifyAuthLost) {
      notifyPortalAuthLost();
    }
    throw new ApiError((payload as { message?: string }).message || "Portal login required", 401);
  }
  if (!response.ok) {
    throw new Error((payload as { message?: string }).message || `Request failed (${response.status})`);
  }
  return payload as T;
}

function request(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(path, { credentials: "same-origin", ...init });
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
  getPortalSession: () =>
    request("/api/portal/session").then((res) => parseJson<PortalSession>(res, { notifyAuthLost: false })),
  login: (username: string, password: string) =>
    request("/api/portal/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    }).then((res) => parseJson<PortalSession>(res, { notifyAuthLost: false })),
  logout: () =>
    request("/api/portal/logout", { method: "POST" }).then((res) =>
      parseJson<PortalSession>(res, { notifyAuthLost: false })
    ),
  getStats: () => request("/api/stats").then((res) => parseJson<DashboardStats>(res)),
  getConfig: () => request("/api/config").then((res) => parseJson<PortalConfig>(res)),
  updateConfig: (body: { responseStatus?: number; responseDelayMs?: number }) =>
    request("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then((res) => parseJson<PortalConfig>(res)),
  getCatalog: () => request("/api/events").then((res) => parseJson<EventCatalog>(res)),
  getCatalogEvent: (eventType: string) =>
    request(`/api/events/${encodeURIComponent(eventType)}`).then((res) => parseJson<CatalogEvent>(res)),
  listWebhookEvents: (query: EventListQuery = {}) =>
    request(`/api/webhook-events${queryString(query)}`).then((res) => parseJson<EventListResult>(res)),
  getWebhookEvent: (id: string) =>
    request(`/api/webhook-events/${id}`).then((res) => parseJson<WebhookEvent>(res)),
  clearWebhookEvents: () =>
    request("/api/webhook-events", { method: "DELETE" }).then((res) => parseJson<{ deleted: number }>(res)),
  exportWebhookEvents: async (query: EventListQuery, format: "json" | "csv") => {
    const qs = queryString(query);
    const separator = qs ? "&" : "?";
    const response = await request(`/api/webhook-events/export${qs}${separator}format=${format}`);
    if (response.status === 401) {
      notifyPortalAuthLost();
      const payload = await response.json().catch(() => ({}));
      throw new ApiError((payload as { message?: string }).message || "Portal login required", 401);
    }
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error((payload as { message?: string }).message || `Export failed (${response.status})`);
    }
    const blob = await response.blob();
    const count = Number(response.headers.get("X-Export-Count") ?? "0");
    const total = Number(response.headers.get("X-Export-Total") ?? "0");
    const truncated = response.headers.get("X-Export-Truncated") === "true";
    const fallback = `webhook-events.${format}`;
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const match = disposition.match(/filename="([^"]+)"/);
    const filename = match?.[1] || fallback;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    return { count, total, truncated, filename };
  },
  getHealth: () =>
    request("/health").then((res) => parseJson<{ status: string; service: string; timestamp: string }>(res)),
  sendWebhook: (payload: unknown, apiKey?: string) => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }
    return request("/webhooks/iri", {
      method: "POST",
      headers,
      body: JSON.stringify(payload)
    }).then(async (res) => {
      const body = await res.json().catch(() => ({}));
      return { status: res.status, body };
    });
  }
};
