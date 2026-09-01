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
  events: CatalogEvent[];
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

export interface PortalConfig {
  responseStatus: number;
  responseDelayMs: number;
  authEnabled: boolean;
  iriVersion: string;
  webhookPath: string;
  publicBaseUrl: string;
  webhookUrl: string;
  allowedResponseStatuses: number[];
  catalogVersion: string;
}

export interface EventListQuery {
  eventType?: string;
  policyNumber?: string;
  status?: string;
  from?: string;
  search?: string;
}
