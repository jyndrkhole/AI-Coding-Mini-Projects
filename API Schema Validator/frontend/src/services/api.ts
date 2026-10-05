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
    const backendHint =
      'Start the Schema Validator backend: `cd schema-validator && PYTHONPATH=. uvicorn backend.main:app --reload --port 8010`';

    // Vite proxy often surfaces a dead backend as 500/502/503/504
    if (
      status === 404 ||
      status === 500 ||
      status === 502 ||
      status === 503 ||
      status === 504 ||
      ax.code === 'ERR_NETWORK' ||
      ax.code === 'ECONNREFUSED' ||
      ax.message?.includes('Network Error')
    ) {
      // Keep real backend validation errors (JSON body with our shape) intact
      const data = ax.response?.data;
      if (
        status === 500 &&
        data &&
        typeof data === 'object' &&
        ('detail' in data || 'errors' in data || 'valid' in data)
      ) {
        const detail = (data as { detail?: string }).detail;
        return new Error(typeof detail === 'string' ? detail : ax.message);
      }
      return new Error(
        `Cannot reach Schema Validator API${status ? ` (${status})` : ''}. ${backendHint}`,
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
