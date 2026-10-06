import { clearAccessToken, getAccessToken, silentRefresh } from "./auth";

interface ApiOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  formData?: URLSearchParams;
  /** Public endpoints: no bearer token and no refresh-and-redirect on 401. */
  anonymous?: boolean;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  let response = await apiRaw(path, options);

  if (response.status === 401 && !options.anonymous) {
    if (await silentRefresh()) {
      response = await apiRaw(path, options);
    }
    if (response.status === 401) {
      clearAccessToken();
      const here = window.location.pathname + window.location.search;
      window.location.href = `/login?redirect=${encodeURIComponent(here)}`;
      throw new ApiError(401, "Your session has expired. Please sign in again.", null);
    }
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, problemMessage(response.status, body), body);
  }

  if (response.status === 202 || response.status === 204) return undefined as T;
  return response.json();
}

export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  let response = await apiRaw(path, {});
  if (response.status === 401 && (await silentRefresh())) {
    response = await apiRaw(path, {});
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, problemMessage(response.status, body), body);
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? fallbackName;
  saveBlob(await response.blob(), filename);
}

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function apiRaw(path: string, options: ApiOptions): Promise<Response> {
  const { body: payload, formData, anonymous, headers: extraHeaders, ...init } = options;
  const headers: Record<string, string> = {};
  const token = getAccessToken();
  if (token && !anonymous) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let body: BodyInit | undefined;
  if (formData) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = formData;
  } else if (payload !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(payload);
  }

  return fetch(`/api${path}`, {
    ...init,
    credentials: "same-origin",
    headers: { ...headers, ...(extraHeaders as Record<string, string> | undefined) },
    body,
  });
}

interface ValidationIssue {
  msg?: string;
  message?: string;
  loc?: (string | number)[];
  field?: string;
}

export function problemMessage(status: number, body: unknown): string {
  if (status === 429) return "Too many attempts. Please wait a few minutes and try again.";
  if (body && typeof body === "object") {
    const record = body as { detail?: unknown; errors?: ValidationIssue[] };
    if (Array.isArray(record.errors) && record.errors.length > 0) {
      return record.errors.map((issue) => issue.message ?? issue.msg).join(" ");
    }
    if (typeof record.detail === "string") return record.detail;
    if (Array.isArray(record.detail) && record.detail.length > 0) {
      return (record.detail as ValidationIssue[])
        .map((issue) => {
          const field = issue.loc?.filter((part) => part !== "body").join(".");
          return field ? `${field}: ${issue.msg}` : issue.msg;
        })
        .join(" ");
    }
  }
  return "Request failed";
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
