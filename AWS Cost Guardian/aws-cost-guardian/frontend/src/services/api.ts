export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export async function apiPost<T>(path: string): Promise<T> {
  return request<T>(path, { method: "POST" });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError("Could not reach the FinOps API. Start the backend and try again.");
  }

  if (!response.ok) {
    let detail = "Could not load FinOps data.";
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string" && body.detail.trim()) {
        detail = body.detail;
      }
    } catch {
      detail = "Could not load FinOps data.";
    }
    throw new ApiError(detail);
  }

  return (await response.json()) as T;
}
