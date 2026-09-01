export const WEBHOOK_EVENTS_SCHEMA = `
CREATE TABLE IF NOT EXISTS webhook_events (
  id TEXT PRIMARY KEY,
  event_type TEXT,
  policy_number TEXT,
  received_at TEXT NOT NULL,
  request_method TEXT NOT NULL,
  request_path TEXT NOT NULL,
  headers_json TEXT NOT NULL,
  payload_json TEXT,
  source_ip TEXT,
  response_status INTEGER,
  response_body TEXT,
  processing_time_ms INTEGER,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_webhook_events_received_at ON webhook_events(received_at);
CREATE INDEX IF NOT EXISTS idx_webhook_events_event_type ON webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_events_policy_number ON webhook_events(policy_number);
CREATE INDEX IF NOT EXISTS idx_webhook_events_response_status ON webhook_events(response_status);
`;
