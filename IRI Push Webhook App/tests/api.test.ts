import { describe, expect, it } from "vitest";
import request from "supertest";
import { createTestApp } from "./helpers.ts";

describe("internal APIs", () => {
  it("returns dashboard stats after receiving webhooks", async () => {
    const app = createTestApp();
    await request(app)
      .post("/webhooks/iri")
      .send({ eventType: "applicationStatus.v1.applicationReceived", policyNumber: "A" })
      .expect(200);
    await request(app).put("/api/config").send({ responseStatus: 500 }).expect(200);
    await request(app)
      .post("/webhooks/iri")
      .send({ eventType: "applicationStatus.v1.applicationCancelled", policyNumber: "B" })
      .expect(500);

    const stats = await request(app).get("/api/stats").expect(200);
    expect(stats.body.totalEvents).toBe(2);
    expect(stats.body.successful).toBe(1);
    expect(stats.body.failed).toBe(1);
    expect(stats.body.eventTypes).toBe(2);
    expect(stats.body.eventsToday).toBe(2);
  });

  it("returns runtime config", async () => {
    const app = createTestApp();
    const config = await request(app).get("/api/config").expect(200);
    expect(config.body.webhookPath).toBe("/webhooks/iri");
    expect(config.body.responseStatus).toBe(200);
    expect(config.body.allowedResponseStatuses).toContain(503);
  });
});
