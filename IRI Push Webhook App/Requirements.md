Build a complete internal application called:

"IRI Push Notification Test Portal"

============================================================

1. PURPOSE

============================================================

We are implementing the IRI Application Status Push Notification

functionality.

The actual client/distributor webhook endpoints are not yet available.

This application will temporarily act as a dummy/internal webhook

receiver so that our backend development team can:

1. Send IRI Push Notification POST requests.

2. Test all notification events.

3. Inspect received requests.

4. Validate payloads.

5. Test HTTP success/failure scenarios.

6. Test retry and timeout behavior from our backend.

7. View webhook activity through a web UI.

8. Demonstrate the functionality internally to stakeholders.

This is a TEST HARNESS / INTERNAL WEBHOOK RECEIVER.

It must NOT contain carrier-specific business logic.

============================================================

2. IRI SPECIFICATION

============================================================

Use the IRI Application Status Push Notification specification provided

with this project as the authoritative source for:

- Event names

- Event descriptions

- Payload structures

- Field names

- Data types

- Required/optional fields

- Sample payloads where available

The IRI specification is available at:

[https://specs.dfa.irionline.org/api-viewer.html?api=appstatuspushNotifications&version=v1](https://specs.dfa.irionline.org/api-viewer.html?api=appstatuspushNotifications&version=v1)

IMPORTANT:

The actual IRI YAML specification will be provided to you as a project

file.

Read the YAML before implementing the event catalogue.

Do NOT invent event names or payload fields.

============================================================

3. CORE WEBHOOK ENDPOINT

============================================================

Create one generic webhook endpoint:

POST /webhooks/iri

The endpoint must accept JSON requests.

Example:

POST /webhooks/iri

Content-Type: application/json

{

  "eventType": "applicationComplete",

  "policyNumber": "POL12345",

  ...

}

IMPORTANT:

Do not create separate primary endpoints for every event.

DO NOT design the system as:

POST /webhooks/applicationComplete

POST /webhooks/applicationCancelled

POST /webhooks/fundingActionNeeded

etc.

Instead, use the single generic endpoint:

POST /webhooks/iri

The receiver must be capable of accepting all current and future IRI

Push Notification events.

============================================================

4. EVENT IDENTIFICATION

============================================================

The event type should be identified according to the actual IRI

specification.

Do not assume that "eventType" is necessarily the exact field unless

the YAML confirms it.

Inspect the provided YAML and use the actual IRI mechanism for identifying

the notification/event.

The application should still maintain an internal event catalogue for:

- UI display

- Event selection

- Sample payloads

- Descriptions

- Filtering

- Developer testing

Unknown/future event types should NOT be rejected solely because they

are missing from the catalogue.

They should still be accepted and logged.

============================================================

5. TECHNOLOGY STACK

============================================================

Backend:

- Node.js

- TypeScript

- Express.js

Frontend:

- React

- TypeScript

- Modern responsive UI

Database:

- SQLite

Use a lightweight architecture.

Do NOT over-engineer.

Keep the project easy for another developer to understand and maintain.

============================================================

6. PROJECT STRUCTURE

============================================================

Use a clean structure similar to:

src/

  api/

    controllers/

    routes/

    middleware/

  services/

  repositories/

  models/

  database/

  config/

  types/

  utils/

  app.ts

  server.ts

frontend/

  src/

    components/

    pages/

    services/

    types/

    hooks/

config/

  iri/

    v1/

      events.json

tests/

[README.md](http://README.md)

.env.example

Dockerfile

docker-compose.yml

============================================================

7. WEBHOOK REQUEST LOGGING

============================================================

Every incoming webhook request must be persisted.

Capture:

- Internal event ID

- Event type

- Policy number, if available

- Received timestamp

- HTTP method

- Request path

- Request headers

- Complete request payload

- Source IP, if available

- HTTP response status

- Response body

- Processing duration

- Created timestamp

Store JSON fields as JSON text in SQLite.

IMPORTANT:

Never expose credentials/secrets in the UI.

Mask sensitive headers.

For example:

Authorization: Bearer ********

============================================================

8. DATABASE

============================================================

Create a SQLite table:

webhook_events

Suggested fields:

id

event_type

policy_number

received_at

request_method

request_path

headers_json

payload_json

source_ip

response_status

response_body

processing_time_ms

created_at

Create the database automatically when the application starts.

============================================================

9. WEBHOOK RESPONSE

============================================================

Default response:

HTTP 200

{

  "status": "received",

  "message": "Webhook received successfully",

  "eventId": "<internal-event-id>"

}

The response behavior must be configurable.

Environment variables:

WEBHOOK_RESPONSE_STATUS=200

WEBHOOK_RESPONSE_DELAY_MS=0

Support simulation of:

200

201

202

400

401

403

409

500

503

This is required so that our backend Push Notification delivery logic

can be tested for:

- Success

- Retry

- Failure

- Timeout

- Error handling

============================================================

10. AUTHENTICATION

============================================================

Support optional API-key authentication.

Environment variables:

WEBHOOK_AUTH_ENABLED=false

WEBHOOK_API_KEY=

When enabled, support:

X-API-Key: <key>

Keep authentication configurable.

Do not hard-code credentials.

If Authorization headers are used, mask them in logs/UI.

============================================================

11. HEALTH CHECK

============================================================

Create:

GET /health

Response:

{

  "status": "ok",

  "service": "iri-push-notification-test-portal",

  "timestamp": "..."

}

============================================================

12. INTERNAL API

============================================================

Create REST APIs for the frontend:

GET /api/webhook-events

GET /api/webhook-events/:id

DELETE /api/webhook-events

GET /api/stats

GET /api/events

GET /api/events/:eventType

GET /api/config

These APIs should provide the UI with event history and configuration.

============================================================

13. DASHBOARD UI

============================================================

Build a clean, modern developer-focused dashboard.

Application title:

IRI Push Notification

Internal Test Portal

Header:

IRI Push Notification

Webhook Test Portal

Status:

● Webhook Receiver Online

Display webhook URL:

POST https://<host>/webhooks/iri

Provide:

[ COPY URL ]

============================================================

14. DASHBOARD STATISTICS

============================================================

Display cards:

Total Events

Successful

Failed

Events Today

Event Types

Example:

┌────────────────┐

│ Total Events   │

│      128       │

└────────────────┘

┌────────────────┐

│ Successful     │

│      121       │

└────────────────┘

┌────────────────┐

│ Failed         │

│       7        │

└────────────────┘

┌────────────────┐

│ Event Types    │

│       12       │

└────────────────┘

============================================================

15. RECENT EVENTS

============================================================

Display a table:

Timestamp

Event

Policy Number

Status

Duration

Actions

Example:

13:05:21 | applicationComplete | POL123 | 200 | 42ms | View

13:04:18 | fundingActionNeeded | POL456 | 200 | 38ms | View

13:02:44 | suitability | POL789 | 500 | 51ms | View

Clicking an event opens a detailed view.

============================================================

16. EVENT DETAIL VIEW

============================================================

Show:

EVENT INFORMATION

Event ID

Event Type

Policy Number

Received Time

HTTP Status

Processing Time

Source IP

REQUEST HEADERS

Display key/value headers.

Mask:

Authorization

API keys

Tokens

Secrets

REQUEST PAYLOAD

Display formatted JSON.

Features:

- Syntax highlighting

- Expand/collapse

- Copy JSON

- Pretty print

RESPONSE

Display:

HTTP Status

Response Body

Processing Time

============================================================

17. EVENT FILTERING

============================================================

Provide filters:

Event Type

Policy Number

HTTP Status

Date

Search

Event Type dropdown should be populated from:

config/iri/v1/events.json

Do not hard-code the event list into React components.

============================================================

18. SEND TEST WEBHOOK

============================================================

Create a dedicated:

"Send Test Notification"

page.

UI:

Event Type

[ Select IRI Event ▼ ]

Policy Number

[ POL123456 ]

Payload

[ JSON Editor ]

Buttons:

[ Format JSON ]

[ Reset Payload ]

[ Send Webhook ]

When an event is selected:

1. Load its sample payload.

2. Display the event description.

3. Allow the developer to edit the payload.

4. Allow the developer to send it.

The payload editor must NOT prevent developers from modifying the

sample payload.

============================================================

19. SAMPLE PAYLOADS

============================================================

Generate sample payloads from the provided IRI YAML specification.

Do NOT invent fields.

Do NOT silently modify the IRI schema.

If the YAML does not provide an example value, use a reasonable

placeholder while preserving the correct field structure.

Clearly label these as:

"Test Payload"

not as production payloads.

============================================================

20. CURL EXAMPLE

============================================================

The UI should include a Developer Usage section.

Example:

curl -X POST [http://localhost:3000/webhooks/iri](http://localhost:3000/webhooks/iri) \

  -H "Content-Type: application/json" \

  -H "X-API-Key: test-token" \

  -d '{

    ...

  }'

Provide:

[ COPY CURL ]

The actual example should use the selected IRI event and its sample

payload.

============================================================

21. FAILURE SIMULATION

============================================================

Provide a settings/test section where developers can configure:

Response Status:

200

201

202

400

401

403

409

500

503

Response Delay:

0 ms

500 ms

1000 ms

3000 ms

Custom

These settings are for testing our backend delivery engine.

For example:

Backend

   |

   | POST webhook

   ↓

Test Portal

   |

   | 500

   ↓

Backend Retry Logic

============================================================

22. REAL-TIME EVENT DISPLAY

============================================================

When a webhook is received, the dashboard should update automatically.

Preferred:

Server-Sent Events (SSE)

Alternative:

Polling

Do not introduce unnecessary infrastructure.

A simple SSE implementation is preferred if it remains clean.

============================================================

23. IRI EVENT CATALOG

============================================================

The event catalogue must be maintained separately from business logic.

Location:

config/iri/v1/events.json

The catalogue should contain:

- Event name

- Display name

- Description

- Sample payload

- Enabled flag

- IRI version

Example structure:

{

  "version": "v1",

  "events": [

    {

      "eventType": "...",

      "displayName": "...",

      "description": "...",

      "enabled": true,

      "samplePayload": {}

    }

  ]

}

IMPORTANT:

Populate the actual catalogue from the provided IRI YAML.

Do not invent the list.

============================================================

24. FUTURE VERSION SUPPORT

============================================================

Design the configuration so future IRI versions can be added.

Example:

config/

  iri/

    v1/

      events.json

    v2/

      events.json

Initial implementation:

v1 only.

Do not hard-code v1 into the core webhook processing logic.

============================================================

25. UNKNOWN EVENTS

============================================================

The receiver must accept unknown/future events.

Example:

POST /webhooks/iri

with an event not currently present in events.json.

Result:

- Accept request

- Persist request

- Display event as "Unknown/Future Event"

- Do not fail the webhook only because the event is unknown

This is important for forward compatibility.

============================================================

26. SECURITY

============================================================

Even though this is an internal test tool:

- Validate JSON

- Set reasonable request body size limit

- Mask secrets

- Make CORS configurable

- Optional authentication

- Basic rate limiting if simple

- Do not execute incoming payload content

- Do not log credentials

============================================================

27. DOCKER

============================================================

Create:

Dockerfile

docker-compose.yml

The application should run with:

npm install

npm run dev

and:

docker compose up

SQLite data should be persisted through a volume.

============================================================

28. TESTING

============================================================

Create unit/integration tests for:

1. POST valid webhook

2. POST invalid JSON

3. POST without authentication when authentication is enabled

4. POST with valid authentication

5. Webhook persistence

6. GET events

7. GET event by ID

8. Delete events

9. Health endpoint

10. HTTP failure simulation

11. Response delay

12. Unknown/future event

13. Event catalogue loading

Run all tests before completing the implementation.

============================================================

29. README

============================================================

Create a detailed README containing:

1. Purpose

2. Architecture

3. Technology stack

4. Project structure

5. Local setup

6. Environment variables

7. Webhook endpoint

8. API endpoints

9. Curl examples

10. UI usage

11. Event catalogue

12. Failure simulation

13. Authentication

14. Docker deployment

15. Testing

16. Future IRI version support

Include a Mermaid architecture diagram.

Example:

flowchart TD

    A[Backend Push Notification Service]

      -->|HTTP POST| B[IRI Webhook Test Portal]

    B --> C[Authentication]

    C --> D[Webhook Controller]

    D --> E[Webhook Service]

    E --> F[(SQLite)]

    E --> G[HTTP Response]

    F --> H[Web Dashboard]

============================================================

30. IMPORTANT ARCHITECTURAL PRINCIPLE

============================================================

Keep these responsibilities separate.

OUR REAL BACKEND:

Event Detection

      ↓

Event Mapping

      ↓

Payload Generation

      ↓

Subscriber Lookup

      ↓

Webhook Delivery

      ↓

Retry / Failure Handling

      ↓

Audit

THIS APPLICATION:

Receive HTTP POST

      ↓

Authenticate

      ↓

Store Request

      ↓

Display Request

      ↓

Return Configurable Response

Do NOT move event generation, subscriber management, retry logic,

carrier integration, or business logic into this application.

============================================================

31. UI DESIGN

============================================================

The UI should look professional enough for an internal stakeholder

demonstration.

Use:

- Clean dashboard

- Responsive layout

- Cards for statistics

- Event table

- Status indicators

- JSON syntax highlighting

- Expandable payload viewer

- Copy buttons

- Clear navigation

- Simple settings page

- Developer-friendly typography

Keep it simple rather than creating an overly complex enterprise UI.

Suggested navigation:

Dashboard

Events

Send Test Notification

Settings

API Documentation

============================================================

32. SWAGGER / OPENAPI

============================================================

Add Swagger/OpenAPI documentation.

Expose:

/api-docs

Document:

POST /webhooks/iri

GET /health

GET /api/webhook-events

GET /api/webhook-events/:id

GET /api/stats

GET /api/events

Use the IRI YAML specification as reference for the webhook request

documentation.

Clearly indicate that this is an INTERNAL TEST WEBHOOK RECEIVER.

============================================================

33. FINAL IMPLEMENTATION REQUIREMENT

============================================================

After implementation:

1. Build the application.

2. Run the backend.

3. Run the frontend.

4. Run all tests.

5. Fix errors.

6. Verify POST /webhooks/iri using curl.

7. Verify the received event appears in the UI.

8. Verify event details.

9. Verify failure simulation.

10. Verify unknown event handling.

At the end provide:

- Final project structure

- Commands to run

- Webhook URL

- Swagger URL

- Example curl

- Environment variables

- Test results

- Any assumptions made

Do not ask unnecessary clarification questions.

Make reasonable implementation decisions and document them.