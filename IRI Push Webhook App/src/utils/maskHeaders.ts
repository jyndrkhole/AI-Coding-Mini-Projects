const SENSITIVE_HEADER = /^(authorization|cookie|set-cookie|x-api-key|api-key|x-auth-token|proxy-authorization)$/i;
const SENSITIVE_NAME = /(token|secret|password|api[_-]?key|authorization)/i;

function maskValue(value: string): string {
  if (/^Bearer\s+/i.test(value)) {
    return "Bearer ********";
  }
  return "********";
}

export function maskHeaders(headers: Record<string, unknown>): Record<string, string> {
  const masked: Record<string, string> = {};
  for (const [key, raw] of Object.entries(headers)) {
    const value = Array.isArray(raw) ? raw.join(", ") : String(raw ?? "");
    if (SENSITIVE_HEADER.test(key) || SENSITIVE_NAME.test(key)) {
      masked[key] = maskValue(value);
    } else {
      masked[key] = value;
    }
  }
  return masked;
}

export function flattenHeaders(headers: Record<string, unknown>): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, raw] of Object.entries(headers)) {
    result[key] = Array.isArray(raw) ? raw.join(", ") : String(raw ?? "");
  }
  return result;
}
