import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { afterEach, describe, expect, it } from "vitest";
import request from "supertest";
import { clearSourceAuthCache } from "../src/services/sourceNotifications.ts";
import { createTestApp } from "./helpers.ts";

let source: Server | undefined;

function listen(handler: (req: IncomingMessage, res: ServerResponse) => void): Promise<string> {
  source = createServer(handler);
  return new Promise((resolve) => {
    source!.listen(0, "127.0.0.1", () => {
      const address = source!.address();
      const port = address && typeof address === "object" ? address.port : 0;
      resolve(`http://127.0.0.1:${port}`);
    });
  });
}

afterEach(async () => {
  clearSourceAuthCache();
  delete process.env.SOURCE_API_BASE_URL;
  delete process.env.SOURCE_API_BASE_URL_QA;
  delete process.env.SOURCE_API_BASE_URL_INT;
  delete process.env.SOURCE_API_BASE_URL_PROD;
  delete process.env.SOURCE_API_KEY;
  delete process.env.SOURCE_X_API_KEY;
  delete process.env.PORTAL_ENVIRONMENT;
  if (!source) {
    return;
  }
  const closing = source;
  source = undefined;
  await new Promise<void>((resolve) => closing.close(() => resolve()));
});

describe("source reconciliation", () => {
  it("requires a source base URL for this portal", async () => {
    delete process.env.SOURCE_API_BASE_URL;
    const app = createTestApp();
    const response = await request(app)
      .get("/api/reconciliation")
      .query({ startTime: "2026-10-01T00:00:00.000Z", endTime: "2026-10-02T00:00:00.000Z" })
      .expect(400);
    expect(response.body.message).toMatch(/SOURCE_API_BASE_URL/);
  });

  it("requires a source API key before calling getAuthToken", async () => {
    const base = await listen((_req, res) => {
      res.statusCode = 500;
      res.end("should not be called");
    });
    process.env.SOURCE_API_BASE_URL = base;
    delete process.env.SOURCE_API_KEY;
    const app = createTestApp();
    const response = await request(app)
      .get("/api/reconciliation")
      .query({ startTime: "2026-10-01T00:00:00.000Z", endTime: "2026-10-02T00:00:00.000Z" })
      .expect(400);
    expect(response.body.message).toMatch(/SOURCE_API_KEY/);
  });

  it("uses the source URL configured for this environment", async () => {
    let seenPath = "";
    const base = await listen((req, res) => {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");
      seenPath = url.pathname;
      res.setHeader("Content-Type", "application/json");
      if (url.pathname === "/getAuthToken") {
        res.end(JSON.stringify({ token: "env-token" }));
        return;
      }
      res.end(JSON.stringify({ totalEvents: 0, events: [] }));
    });
    delete process.env.SOURCE_API_BASE_URL;
    process.env.PORTAL_ENVIRONMENT = "INT";
    process.env.SOURCE_API_BASE_URL_QA = "http://127.0.0.1:9";
    process.env.SOURCE_API_BASE_URL_INT = base;
    process.env.SOURCE_API_BASE_URL_PROD = "http://127.0.0.1:9";
    process.env.SOURCE_API_KEY = "source-key";
    const app = createTestApp();
    const response = await request(app)
      .get("/api/reconciliation")
      .query({ startTime: "2026-10-01T00:00:00.000Z", endTime: "2026-10-02T00:00:00.000Z" })
      .expect(200);
    expect(seenPath).toBe("/v1/application-notifications/reconciliation");
    expect(response.body.sourceBaseUrl).toBe(base);
    const config = await request(app).get("/api/config").expect(200);
    expect(config.body.portalEnvironment).toBe("INT");
    expect(config.body.sourceApiBaseUrl).toBe(base);
  });

  it("sends the source x-api-key entered by the user", async () => {
    let authKey = "";
    const base = await listen((req, res) => {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");
      res.setHeader("Content-Type", "application/json");
      if (url.pathname === "/getAuthToken") {
        authKey = String(req.headers["x-api-key"] ?? "");
        res.end(JSON.stringify({ token: "user-token" }));
        return;
      }
      res.end(JSON.stringify({ eventId: "evt-9" }));
    });
    process.env.SOURCE_API_BASE_URL = base;
    process.env.SOURCE_API_KEY = "server-key";
    const app = createTestApp();
    const response = await request(app)
      .get("/api/reconciliation/events/evt-9")
      .set("X-Source-Api-Key", "user-entered-key")
      .expect(200);
    expect(authKey).toBe("user-entered-key");
    expect(response.body.sourceStatus).toBe(200);
    expect(response.body.payload).toMatchObject({ eventId: "evt-9" });
  });

  it("calls the source endpoint entered for the test instead of the environment default", async () => {
    let authKey = "";
    const base = await listen((req, res) => {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");
      res.setHeader("Content-Type", "application/json");
      if (url.pathname === "/getAuthToken") {
        authKey = String(req.headers["x-api-key"] ?? "");
        res.end(JSON.stringify({ token: "typed-endpoint-token" }));
        return;
      }
      res.end(JSON.stringify({ eventId: "evt-typed" }));
    });
    process.env.SOURCE_API_BASE_URL = "http://127.0.0.1:9";
    process.env.SOURCE_API_KEY = "server-key";
    const app = createTestApp();
    const response = await request(app)
      .get("/api/reconciliation/events/evt-typed")
      .set("X-Source-Base-Url", base)
      .set("X-Source-Api-Key", "typed-key")
      .expect(200);
    expect(authKey).toBe("typed-key");
    expect(response.body.sourceBaseUrl).toBe(base);
    expect(response.body.payload).toMatchObject({ eventId: "evt-typed" });
  });

  it("treats a pasted reconciliation URL as the source base and still calls getAuthToken first", async () => {
    const seen: string[] = [];
    const base = await listen((req, res) => {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");
      seen.push(`${req.method} ${url.pathname}`);
      res.setHeader("Content-Type", "application/json");
      if (url.pathname === "/api/getAuthToken") {
        res.end(JSON.stringify({ token: "base-token" }));
        return;
      }
      res.end(JSON.stringify({ totalEvents: 0, events: [] }));
    });
    process.env.SOURCE_API_BASE_URL = "http://127.0.0.1:9";
    delete process.env.SOURCE_API_KEY;
    const app = createTestApp();
    const response = await request(app)
      .get("/api/reconciliation")
      .query({ startTime: "2026-10-01T00:00:00.000Z", endTime: "2026-10-02T00:00:00.000Z" })
      .set("X-Source-Base-Url", `${base}/api/v1/application-notifications/reconciliation?startTime=2026-09-09`)
      .set("X-Source-Api-Key", "typed-key")
      .expect(200);
    expect(seen).toEqual(["POST /api/getAuthToken", "GET /api/v1/application-notifications/reconciliation"]);
    expect(response.body.sourceBaseUrl).toBe(`${base}/api`);
  });

  it("rejects a source endpoint that is not an http URL", async () => {
    process.env.SOURCE_API_BASE_URL = "http://127.0.0.1:9";
    process.env.SOURCE_API_KEY = "source-key";
    const app = createTestApp();
    const response = await request(app)
      .get("/api/reconciliation/events/evt-9")
      .set("X-Source-Base-Url", "not-a-url")
      .expect(400);
    expect(response.body.message).toMatch(/http/);
  });

  it("calls this environment's source reconciliation API and marks stored events", async () => {
    const seen: { method: string; path: string; key: string; authorization: string; correlation: string }[] = [];
    let seenQuery = new URLSearchParams();
    const base = await listen((req, res) => {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");
      seen.push({
        method: req.method ?? "",
        path: url.pathname,
        key: String(req.headers["x-api-key"] ?? ""),
        authorization: String(req.headers.authorization ?? ""),
        correlation: String(req.headers.correlationid ?? "")
      });
      seenQuery = url.searchParams;
      res.setHeader("Content-Type", "application/json");
      if (url.pathname === "/getAuthToken") {
        res.end(JSON.stringify({ token: "source-token-value" }));
        return;
      }
      res.end(
        JSON.stringify({
          totalEvents: 2,
          events: [
            { eventId: "evt-stored", policyNumber: "P1", id: "APP-1", status: "received" },
            { eventId: "evt-missing", policyNumber: "P2", id: "APP-2", status: "inProgress" }
          ]
        })
      );
    });

    process.env.SOURCE_API_BASE_URL = base;
    process.env.SOURCE_API_KEY = "source-key";
    const app = createTestApp();
    await request(app)
      .post("/webhooks/iri")
      .send({
        eventId: "evt-stored",
        policyNumber: "P1",
        eventType: "applicationStatus.v1.applicationReceived"
      })
      .expect(200);

    const response = await request(app)
      .get("/api/reconciliation")
      .query({
        startTime: "2026-10-01T00:00:00.000Z",
        endTime: "2026-10-02T00:00:00.000Z",
        associatedFirmId: "FIRM-1",
        correlationId: "corr-1"
      })
      .expect(200);

    expect(seen.map((call) => `${call.method} ${call.path}`)).toEqual([
      "POST /getAuthToken",
      "GET /v1/application-notifications/reconciliation"
    ]);
    expect(seen[0]?.key).toBe("source-key");
    expect(seen[0]?.authorization).toBe("");
    expect(seen[1]?.key).toBe("");
    expect(seen[1]?.authorization).toBe("source-token-value");
    expect(seen[1]?.correlation).toBe("corr-1");
    expect(seenQuery.get("startTime")).toBe("2026-10-01T00:00:00.000Z");
    expect(seenQuery.get("endTime")).toBe("2026-10-02T00:00:00.000Z");
    expect(seenQuery.get("associatedFirmId")).toBe("FIRM-1");
    expect(response.body.sourceBaseUrl).toBe(base);
    expect(response.body.sourceStatus).toBe(200);
    expect(response.body.storedCount).toBe(1);
    expect(response.body.missingCount).toBe(1);
    expect(response.body.events[0].stored).toBe(true);
    expect(response.body.events[0].portalEventId).toEqual(expect.any(String));
    expect(response.body.events[1]).toMatchObject({ eventId: "evt-missing", stored: false, portalEventId: null });
  });

  it("calls the source event API with the auth token and keeps a source 401 from logging the portal out", async () => {
    const seen: { method: string; path: string; authorization: string }[] = [];
    const base = await listen((req, res) => {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");
      seen.push({
        method: req.method ?? "",
        path: url.pathname,
        authorization: String(req.headers.authorization ?? "")
      });
      res.setHeader("Content-Type", "application/json");
      if (url.pathname === "/getAuthToken") {
        res.end(JSON.stringify({ access_token: "event-token" }));
        return;
      }
      res.statusCode = 401;
      res.end(JSON.stringify({ message: "Unauthorized" }));
    });
    process.env.SOURCE_API_BASE_URL = base;
    process.env.SOURCE_API_KEY = "source-key";
    const app = createTestApp();
    const response = await request(app).get("/api/reconciliation/events/evt-9").expect(200);
    expect(seen.map((call) => call.path)).toEqual([
      "/getAuthToken",
      "/v1/application-notifications/evt-9",
      "/getAuthToken",
      "/v1/application-notifications/evt-9"
    ]);
    expect(seen[1]?.authorization).toBe("event-token");
    expect(response.body.sourceStatus).toBe(401);
    expect(response.body.message).toBe("Unauthorized");
    expect(response.body.stored).toBe(false);
    await request(app).get("/api/config").expect(200);
  });
});
