import axios, { AxiosError } from 'axios';
import type {
  ExplainResponse,
  ExportFormat,
  HealthResponse,
  LLMAction,
  SchemaLoadResponse,
  SchemaSourceType,
  ValidationErrorDetail,
  ValidationRequest,
  ValidationResponse,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
});

function friendlyApiError(error: unknown): Error {
  if (axios.isAxiosError(error)) {
    const ax = error as AxiosError<{ detail?: string; message?: string }>;
    const status = ax.response?.status;
    if (status === 404) {
      return new Error(
        'Schema Validator API not found (404). Start the backend on port 8010: ' +
          '`uvicorn backend.main:app --reload --port 8010` (from schema-validator/ with PYTHONPATH=.).',
      );
    }
    if (status === 502 || status === 503 || ax.code === 'ERR_NETWORK' || ax.code === 'ECONNREFUSED') {
      return new Error(
        'Cannot reach Schema Validator backend. Start it with: ' +
          '`cd schema-validator && PYTHONPATH=. uvicorn backend.main:app --reload --port 8010`',
      );
    }
    const detail = ax.response?.data?.detail || ax.response?.data?.message || ax.message;
    return new Error(typeof detail === 'string' ? detail : ax.message);
  }
  return error instanceof Error ? error : new Error('Request failed');
}

async function withFriendlyErrors<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    throw friendlyApiError(error);
  }
}

export async function loadSchema(params: {
  sourceType: SchemaSourceType;
  content?: string;
  url?: string;
  file?: File | null;
}): Promise<SchemaLoadResponse> {
  return withFriendlyErrors(async () => {
    const form = new FormData();
    form.append('source_type', params.sourceType);
    if (params.content) form.append('content', params.content);
    if (params.url) form.append('url', params.url);
    if (params.file) form.append('file', params.file);

    const { data } = await api.post<SchemaLoadResponse>('/schema/load', form);
    return data;
  });
}

export async function validateSchema(
  request: ValidationRequest,
): Promise<ValidationResponse> {
  return withFriendlyErrors(async () => {
    const { data } = await api.post<ValidationResponse>('/schema/validate', request);
    return data;
  });
}

export async function explainWithAi(params: {
  action: LLMAction;
  schemaContent?: string;
  responseContent?: string;
  errors?: ValidationErrorDetail[];
  provider?: string;
}): Promise<ExplainResponse> {
  return withFriendlyErrors(async () => {
    const { data } = await api.post<ExplainResponse>('/schema/explain', {
      action: params.action,
      schema_content: params.schemaContent,
      response_content: params.responseContent,
      errors: params.errors ?? [],
      provider: params.provider,
    });
    return data;
  });
}

export async function exportReport(params: {
  format: ExportFormat;
  validationResult: ValidationResponse;
  schemaContent?: string;
  responseContent?: string;
}): Promise<Blob> {
  return withFriendlyErrors(async () => {
    const { data } = await api.post(
      '/schema/export',
      {
        format: params.format,
        validation_result: params.validationResult,
        schema_content: params.schemaContent,
        response_content: params.responseContent,
      },
      { responseType: 'blob' },
    );
    return data;
  });
}

export async function healthCheck(): Promise<HealthResponse> {
  return withFriendlyErrors(async () => {
    const { data } = await api.get<HealthResponse>('/health');
    // Guard against another local app occupying the proxied port.
    if (!data?.privacy || data.status !== 'ok') {
      throw new Error(
        'Connected to a different API on the backend port (not Schema Validator). ' +
          'Use port 8010 for this project.',
      );
    }
    return data;
  });
}
