export type SchemaSourceType = 'url' | 'file' | 'text';
export type SchemaFormat = 'openapi' | 'json_schema' | 'unknown';
export type ExportFormat = 'html' | 'json' | 'pdf';
export type LLMAction =
  | 'explain_errors'
  | 'suggest_fix'
  | 'generate_correct_json'
  | 'explain_schema';

export type ErrorCategory =
  | 'missing_field'
  | 'invalid_type'
  | 'enum_violation'
  | 'additional_property'
  | 'invalid_format'
  | 'one_of'
  | 'any_of'
  | 'all_of'
  | 'other';

export interface PrivacyPolicy {
  mode: string;
  remote_schema_fetch: boolean;
  cloud_llm: boolean;
  local_llm: boolean;
  payload_logging: boolean;
  data_residency: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  llm_provider: string;
  privacy: PrivacyPolicy;
}
export interface EndpointInfo {
  path: string;
  method: string;
  operation_id?: string | null;
  summary?: string | null;
  response_codes: string[];
}

export interface SchemaOption {
  name: string;
  path?: string | null;
  description?: string | null;
}

export interface SchemaLoadResponse {
  success: boolean;
  format: SchemaFormat;
  openapi_version?: string | null;
  title?: string | null;
  endpoints: EndpointInfo[];
  schemas: SchemaOption[];
  schema_text?: string | null;
  detected_media_type?: string | null;
  message?: string | null;
  error?: string | null;
}

export interface ValidationErrorDetail {
  category: ErrorCategory;
  message: string;
  json_path: string;
  schema_path: string;
  expected?: unknown;
  actual?: unknown;
  line_number?: number | null;
  validator?: string | null;
}

export interface ValidationSummary {
  total_errors: number;
  missing_fields: number;
  invalid_types: number;
  enum_violations: number;
  additional_properties: number;
  invalid_formats: number;
  other: number;
}

export interface ValidationResponse {
  valid: boolean;
  summary: ValidationSummary;
  errors: ValidationErrorDetail[];
  schema_format: SchemaFormat;
  resolved_schema?: Record<string, unknown> | null;
  message: string;
}

export interface ExplainResponse {
  success: boolean;
  action: LLMAction;
  content: string;
  provider?: string | null;
  model?: string | null;
  error?: string | null;
}

export interface ValidationRequest {
  schema_content: string;
  response_content: string;
  path?: string | null;
  method?: string | null;
  status_code?: string | null;
  schema_name?: string | null;
}
