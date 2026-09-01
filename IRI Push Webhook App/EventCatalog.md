IRI PUSH NOTIFICATION EVENT CATALOG GENERATION
================================================

Create the file:

config/iri/v1/events.json

Use the provided IRI Application Status Push Notification YAML
specification as the ONLY authoritative source for the event catalogue.

IRI specification reference:

https://specs.dfa.irionline.org/api-viewer.html?api=appstatuspushNotifications&version=v1

First inspect the YAML carefully.

Extract the COMPLETE list of notification events defined by IRI.

For every event, capture:

1. eventType / event name exactly as defined by IRI
2. Friendly display name
3. Description, if defined
4. Payload/schema structure
5. Required fields
6. Optional fields
7. A representative test payload
8. IRI specification version

Do NOT invent events.

Do NOT rename the official event names.

Do NOT remove events.

Do NOT add events based on assumptions.

============================================================
EXPECTED FILE FORMAT
============================================================

Use:

{
  "specification": "IRI Application Status Push Notifications",
  "version": "v1",
  "source": "IRI",
  "events": [
    {
      "eventType": "<exact IRI event name>",
      "displayName": "<friendly display name>",
      "description": "<description>",
      "enabled": true,
      "samplePayload": {
      }
    }
  ]
}

============================================================
SAMPLE PAYLOAD RULES
============================================================

Generate sample payloads from the actual YAML schema.

Use realistic test values where the specification does not provide
examples.

For example:

policyNumber:

"TEST-POLICY-001"

Dates:

"2026-09-01"

Boolean:

true

String:

"TEST"

Numeric:

1000.00

IMPORTANT:

The sample payload must follow the actual IRI schema.

Do not introduce fields that are not defined by the IRI specification.

============================================================
PAYLOAD COMPLETENESS
============================================================

Where practical, include all required fields.

For optional fields:

Include representative optional fields where useful, but do not
misrepresent them as required.

============================================================
VALIDATION
============================================================

After creating events.json:

1. Compare every event against the YAML.
2. Confirm no IRI event is missing.
3. Confirm no invented event exists.
4. Confirm field names match the YAML.
5. Confirm nesting matches the YAML.
6. Confirm data types match the YAML.
7. Confirm required/optional fields are respected.

============================================================
FUTURE VERSION
============================================================

Keep the catalogue version-specific:

config/iri/v1/events.json

Do not mix v2 events into v1.

Future versions can be added as:

config/iri/v2/events.json

============================================================
IMPORTANT
============================================================

The webhook receiver must NOT reject an event just because it does
not exist in events.json.

events.json is a catalogue for:

- UI
- Test payloads
- Developer reference
- Filtering
- Documentation

The actual webhook receiver remains generic and forward-compatible.