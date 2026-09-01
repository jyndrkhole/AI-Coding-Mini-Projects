import { describe, expect, it } from "vitest";
import request from "supertest";
import { createTestApp } from "./helpers.ts";
import { loadCatalog } from "../src/config/eventsCatalog.ts";

describe("event catalogue", () => {
  it("loads the IRI v1 catalogue with all 12 specification events", async () => {
    const app = createTestApp();
    const catalog = await request(app).get("/api/events").expect(200);

    expect(catalog.body.version).toBe("v1");
    expect(catalog.body.source).toBe("IRI");
    expect(catalog.body.events).toHaveLength(12);

    const fileCatalog = loadCatalog("v1");
    const fileTypes = fileCatalog.events.map((event) => event.eventType);
    const apiTypes = catalog.body.events.map((event: { eventType: string }) => event.eventType);
    expect(apiTypes).toEqual(fileTypes);

    const expected = [
      "applicationStatus.v1.applicationReceived",
      "applicationStatus.v1.canSellActionNeeded",
      "applicationStatus.v1.suitabilityActionNeeded",
      "applicationStatus.v1.suitabilityApproved",
      "applicationStatus.v1.documentReviewActionNeeded",
      "applicationStatus.v1.fundingActionNeeded",
      "applicationStatus.v1.fundingTransferRequestSent",
      "applicationStatus.v1.fundingSourceTypeUpdated",
      "applicationStatus.v1.fundingTransferFollowedUp",
      "applicationStatus.v1.fundingReceived",
      "applicationStatus.v1.applicationCompleted",
      "applicationStatus.v1.applicationCancelled"
    ];
    expect(apiTypes).toEqual(expected);
  });

  it("returns a single catalogue event with a sample payload", async () => {
    const app = createTestApp();
    const eventType = "applicationStatus.v1.applicationReceived";
    const response = await request(app).get(`/api/events/${eventType}`).expect(200);
    expect(response.body.eventType).toBe(eventType);
    expect(response.body.samplePayload.eventType).toBe(eventType);
    expect(response.body.samplePayload.notification.cusip).toBe("401B23458");
  });
});
