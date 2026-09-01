export const openApiSpec = {
  openapi: "3.0.3",
  info: {
    title: "IRI Push Notification Test Portal",
    description:
      "INTERNAL TEST WEBHOOK RECEIVER. This service does not implement carrier business logic. It accepts IRI Application Status Push Notification webhooks, persists them, and returns a configurable HTTP response so delivery, retry, and timeout behavior can be tested.",
    version: "1.0.0"
  },
  servers: [{ url: "/", description: "Test portal" }],
  paths: {
    "/webhooks/iri": {
      post: {
        tags: ["Webhook"],
        summary: "Receive an IRI push notification",
        description:
          "Generic receiver for all current and future IRI push notification events. Unknown event types are accepted and stored. Payload shape follows the IRI Application Status Push Notifications specification. Event type is identified by the `eventType` field.",
        parameters: [
          {
            name: "X-API-Key",
            in: "header",
            required: false,
            description: "Required only when WEBHOOK_AUTH_ENABLED=true",
            schema: { type: "string" }
          },
          {
            name: "correlationId",
            in: "header",
            required: false,
            description: "Optional client-supplied identifier from the IRI spec",
            schema: { type: "string" }
          }
        ],
        requestBody: {
          required: true,
          content: {
            "application/json": {
              schema: {
                type: "object",
                required: ["eventType"],
                properties: {
                  eventId: { type: "string" },
                  policyNumber: { type: "string" },
                  id: { type: "string" },
                  status: { type: "string" },
                  eventType: {
                    type: "string",
                    example: "applicationStatus.v1.applicationReceived"
                  },
                  applicationOrigin: { type: "object" },
                  notification: { type: "object" }
                },
                additionalProperties: true
              }
            }
          }
        },
        responses: {
          "200": { description: "Webhook received (default simulated success)" },
          "201": { description: "Simulated created" },
          "202": { description: "Simulated accepted" },
          "400": { description: "Invalid JSON or simulated client error" },
          "401": { description: "Unauthorized or simulated unauthorized" },
          "403": { description: "Simulated forbidden" },
          "409": { description: "Simulated conflict" },
          "500": { description: "Simulated server error" },
          "503": { description: "Simulated unavailable" }
        }
      }
    },
    "/health": {
      get: {
        tags: ["System"],
        summary: "Health check",
        responses: {
          "200": { description: "Service is healthy" }
        }
      }
    },
    "/api/webhook-events": {
      get: {
        tags: ["Internal API"],
        summary: "List received webhook events",
        parameters: [
          { name: "eventType", in: "query", schema: { type: "string" } },
          { name: "policyNumber", in: "query", schema: { type: "string" } },
          { name: "status", in: "query", schema: { type: "integer" } },
          { name: "from", in: "query", schema: { type: "string" } },
          { name: "to", in: "query", schema: { type: "string" } },
          { name: "search", in: "query", schema: { type: "string" } },
          { name: "limit", in: "query", schema: { type: "integer" } },
          { name: "offset", in: "query", schema: { type: "integer" } }
        ],
        responses: { "200": { description: "Event list" } }
      },
      delete: {
        tags: ["Internal API"],
        summary: "Delete all stored webhook events",
        responses: { "200": { description: "Events deleted" } }
      }
    },
    "/api/webhook-events/{id}": {
      get: {
        tags: ["Internal API"],
        summary: "Get a stored webhook event",
        parameters: [{ name: "id", in: "path", required: true, schema: { type: "string" } }],
        responses: {
          "200": { description: "Event detail" },
          "404": { description: "Not found" }
        }
      }
    },
    "/api/stats": {
      get: {
        tags: ["Internal API"],
        summary: "Dashboard statistics",
        responses: { "200": { description: "Stats" } }
      }
    },
    "/api/events": {
      get: {
        tags: ["Catalog"],
        summary: "IRI event catalogue for the configured version",
        responses: { "200": { description: "Catalogue" } }
      }
    },
    "/api/events/{eventType}": {
      get: {
        tags: ["Catalog"],
        summary: "Single catalogue event including sample payload",
        parameters: [{ name: "eventType", in: "path", required: true, schema: { type: "string" } }],
        responses: {
          "200": { description: "Catalogue event" },
          "404": { description: "Not found" }
        }
      }
    },
    "/api/config": {
      get: {
        tags: ["Internal API"],
        summary: "Runtime configuration",
        responses: { "200": { description: "Config" } }
      },
      put: {
        tags: ["Internal API"],
        summary: "Update simulated response status and delay",
        requestBody: {
          content: {
            "application/json": {
              schema: {
                type: "object",
                properties: {
                  responseStatus: { type: "integer" },
                  responseDelayMs: { type: "integer" }
                }
              }
            }
          }
        },
        responses: { "200": { description: "Updated config" } }
      }
    },
    "/api/stream": {
      get: {
        tags: ["Internal API"],
        summary: "Server-Sent Events stream of received webhooks",
        responses: { "200": { description: "SSE stream" } }
      }
    }
  }
};
