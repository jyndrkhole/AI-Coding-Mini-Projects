export interface WebhookEventRow {
  id: string;
  event_type: string | null;
  policy_number: string | null;
  received_at: string;
  request_method: string;
  request_path: string;
  headers_json: string;
  payload_json: string | null;
  source_ip: string | null;
  response_status: number;
  response_body: string;
  processing_time_ms: number;
  created_at: string;
}

export interface WebhookEvent {
  id: string;
  eventType: string | null;
  policyNumber: string | null;
  receivedAt: string;
  requestMethod: string;
  requestPath: string;
  headers: Record<string, string>;
  payload: unknown;
  sourceIp: string | null;
  responseStatus: number;
  responseBody: unknown;
  processingTimeMs: number;
  createdAt: string;
  knownEvent: boolean;
  displayName: string;
}

export interface EventListFilters {
  eventType?: string;
  policyNumber?: string;
  status?: number;
  from?: string;
  to?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface EventListResult {
  total: number;
  events: WebhookEvent[];
}

export interface DashboardStats {
  totalEvents: number;
  successful: number;
  failed: number;
  eventsToday: number;
  eventTypes: number;
}

export interface CatalogEvent {
  eventType: string;
  displayName: string;
  description: string;
  enabled: boolean;
  webhookName?: string;
  schemaName?: string;
  tag?: string;
  requiredFields?: string[];
  optionalFields?: string[];
  samplePayload: Record<string, unknown>;
}

export interface EventCatalog {
  specification: string;
  version: string;
  specificationVersion?: string;
  source: string;
  sourceFile?: string;
  events: CatalogEvent[];
}

export interface RuntimeConfig {
  responseStatus: number;
  responseDelayMs: number;
  authEnabled: boolean;
  iriVersion: string;
  webhookPath: string;
  publicBaseUrl: string;
}

export const ALLOWED_RESPONSE_STATUSES = [
  200, 201, 202, 400, 401, 403, 409, 500, 503
] as const;

export type AllowedResponseStatus = (typeof ALLOWED_RESPONSE_STATUSES)[number];
