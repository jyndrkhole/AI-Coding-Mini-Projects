import { describe, expect, it } from "vitest";
import request from "supertest";
import { createTestApp } from "./helpers.ts";
import { updateRuntimeConfig } from "../src/config/runtimeConfig.ts";

describe("failure simulation", () => {
  it("returns the configured HTTP status", async () => {
    const app = createTestApp();
    await request(app).put("/api/config").send({ responseStatus: 500 }).expect(200);

    const response = await request(app)
      .post("/webhooks/iri")
      .send({ eventType: "applicationStatus.v1.applicationCancelled", policyNumber: "POL-FAIL" })
      .expect(500);

    expect(response.body.status).toBe("error");
    expect(response.body.message).toMatch(/500/);

    const list = await request(app).get("/api/webhook-events").expect(200);
    expect(list.body.events[0].responseStatus).toBe(500);
  });

  it("delays the webhook response by the configured duration", async () => {
    const app = createTestApp();
    updateRuntimeConfig({ responseDelayMs: 80 });
    const started = Date.now();
    const response = await request(app)
      .post("/webhooks/iri")
      .send({ eventType: "applicationStatus.v1.fundingReceived" })
      .expect(200);
    const elapsed = Date.now() - started;
    expect(elapsed).toBeGreaterThanOrEqual(70);

    const detail = await request(app).get(`/api/webhook-events/${response.body.eventId}`).expect(200);
    expect(detail.body.processingTimeMs).toBeGreaterThanOrEqual(70);
  });
});
