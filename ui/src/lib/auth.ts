let accessToken: string | null = null;
let refreshPromise: Promise<boolean> | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string): void {
  accessToken = token;
}

export function clearAccessToken(): void {
  accessToken = null;
}

async function performRefresh(): Promise<boolean> {
  try {
    const res = await fetch("/api/auth/refresh", { method: "POST", credentials: "same-origin" });
    if (!res.ok) {
      accessToken = null;
      return false;
    }
    const data: { access_token: string } = await res.json();
    accessToken = data.access_token;
    return true;
  } catch {
    accessToken = null;
    return false;
  }
}

export function silentRefresh(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = performRefresh().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

export async function ensureSession(): Promise<boolean> {
  if (accessToken) return true;
  return silentRefresh();
}

export async function logout(): Promise<void> {
  try {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
  } finally {
    accessToken = null;
  }
}

export function safeRedirectTarget(target: string | undefined): string {
  if (!target || !target.startsWith("/") || target.startsWith("//")) return "/";
  return target;
}
