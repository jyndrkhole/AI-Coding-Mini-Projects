import { describe, expect, it } from "vitest";
import request from "supertest";
import { createTestApp } from "./helpers.ts";

const samplePayload = {
  eventId: "evt-test-001",
  policyNumber: "P987654321",
  id: "APP-2026-001234",
  applicationOrigin: {
    platform: "DigitalFirst",
    isElectronic: true,
    id: "DF-APP-001234"
  },
  status: "received",
  eventType: "applicationStatus.v1.applicationReceived",
  notification: {
    cusip: "401B23458",
    isActionNeeded: false,
    productName: "Secure Income Annuity Plus"
  }
};

describe("POST /webhooks/iri", () => {
  it("accepts a valid webhook and persists it", async () => {
    const app = createTestApp();
    const response = await request(app)
      .post("/webhooks/iri")
      .send(samplePayload)
      .expect(200);

    expect(response.body.status).toBe("received");
    expect(response.body.message).toBe("Webhook received successfully");
    expect(typeof response.body.eventId).toBe("string");

    const list = await request(app).get("/api/webhook-events").expect(200);
    expect(list.body.total).toBe(1);
    expect(list.body.events[0].eventType).toBe(samplePayload.eventType);
    expect(list.body.events[0].policyNumber).toBe(samplePayload.policyNumber);
    expect(list.body.events[0].responseStatus).toBe(200);
    expect(list.body.events[0].payload.eventType).toBe(samplePayload.eventType);

    const detail = await request(app).get(`/api/webhook-events/${response.body.eventId}`).expect(200);
    expect(detail.body.id).toBe(response.body.eventId);
    expect(detail.body.knownEvent).toBe(true);
  });

  it("rejects invalid JSON with 400 and still persists the attempt", async () => {
    const app = createTestApp();
    const response = await request(app)
      .post("/webhooks/iri")
      .set("Content-Type", "application/json")
      .send("{not-json")
      .expect(400);

    expect(response.body.status).toBe("error");
    expect(response.body.message).toMatch(/invalid json/i);

    const list = await request(app).get("/api/webhook-events").expect(200);
    expect(list.body.total).toBe(1);
    expect(list.body.events[0].responseStatus).toBe(400);
  });

  it("accepts unknown/future event types without rejecting them", async () => {
    const app = createTestApp();
    const payload = {
      eventType: "applicationStatus.v9.brandNewEvent",
      policyNumber: "FUTURE-001",
      status: "inProgress"
    };

    const response = await request(app).post("/webhooks/iri").send(payload).expect(200);
    expect(response.body.status).toBe("received");

    const detail = await request(app).get(`/api/webhook-events/${response.body.eventId}`).expect(200);
    expect(detail.body.eventType).toBe(payload.eventType);
    expect(detail.body.knownEvent).toBe(false);
    expect(detail.body.displayName).toBe("Unknown/Future Event");
  });

  it("returns a stored event by id and 404 for missing ids", async () => {
    const app = createTestApp();
    const created = await request(app).post("/webhooks/iri").send(samplePayload).expect(200);
    await request(app).get(`/api/webhook-events/${created.body.eventId}`).expect(200);
    await request(app).get("/api/webhook-events/does-not-exist").expect(404);
  });

  it("deletes all stored events", async () => {
    const app = createTestApp();
    await request(app).post("/webhooks/iri").send(samplePayload).expect(200);
    const deleted = await request(app).delete("/api/webhook-events").expect(200);
    expect(deleted.body.deleted).toBe(1);
    const list = await request(app).get("/api/webhook-events").expect(200);
    expect(list.body.total).toBe(0);
  });
});
