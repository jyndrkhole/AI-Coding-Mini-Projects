import { describe, expect, it } from "vitest";
import request from "supertest";
import { createTestApp } from "./helpers.ts";

describe("GET /health", () => {
  it("returns service health", async () => {
    const app = createTestApp();
    const response = await request(app).get("/health").expect(200);
    expect(response.body.status).toBe("ok");
    expect(response.body.service).toBe("iri-push-notification-test-portal");
    expect(typeof response.body.timestamp).toBe("string");
  });
});
