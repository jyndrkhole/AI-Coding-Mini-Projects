import { describe, expect, it } from "vitest";
import request from "supertest";
import { createTestApp } from "./helpers.ts";
import { setAuthEnabledForTests } from "../src/config/runtimeConfig.ts";

describe("webhook authentication", () => {
  it("rejects requests without an API key when authentication is enabled", async () => {
    process.env.WEBHOOK_API_KEY = "test-token";
    const app = createTestApp();
    setAuthEnabledForTests(true);

    const response = await request(app)
      .post("/webhooks/iri")
      .send({ eventType: "applicationStatus.v1.applicationReceived" })
      .expect(401);

    expect(response.body.message).toBe("Unauthorized");
  });

  it("accepts requests with a valid API key when authentication is enabled", async () => {
    process.env.WEBHOOK_API_KEY = "test-token";
    const app = createTestApp();
    setAuthEnabledForTests(true);

    const response = await request(app)
      .post("/webhooks/iri")
      .set("X-API-Key", "test-token")
      .send({
        eventType: "applicationStatus.v1.applicationReceived",
        policyNumber: "POL-AUTH"
      })
      .expect(200);

    expect(response.body.status).toBe("received");

    const detail = await request(app).get(`/api/webhook-events/${response.body.eventId}`).expect(200);
    expect(detail.body.headers["x-api-key"]).toBe("********");
  });
});
