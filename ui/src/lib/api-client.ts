import { clearTokens, getAccessToken, silentRefresh } from "./auth";

interface ApiOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  formData?: URLSearchParams;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const response = await apiRaw(path, options);

  if (response.status === 401) {
    const refreshed = await silentRefresh();
    if (refreshed) {
      const retry = await apiRaw(path, options);
      if (retry.ok) return retry.json();
    }
    clearTokens();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new ApiError(response.status, error.detail ?? "Request failed", error);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

async function apiRaw(path: string, options: ApiOptions): Promise<Response> {
  const headers: Record<string, string> = {};
  const token = getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let body: BodyInit | undefined;
  if (options.formData) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = options.formData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  return fetch(`/api${path}`, {
    ...options,
    headers: { ...headers, ...options.headers },
    body,
  });
}

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}
