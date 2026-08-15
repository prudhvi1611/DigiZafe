import { useAuthStore, getRefreshFromSession } from "./auth-store";
import type { TokenPair } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export class ApiClientError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    const detail =
      typeof body === "object" && body && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `HTTP ${status}`;
    super(detail);
    this.status = status;
    this.body = body;
  }
}

async function parseJson(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const store = useAuthStore.getState();
  const refresh = store.refreshToken || getRefreshFromSession();
  if (!refresh) return null;

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) {
          store.clear();
          return null;
        }
        const data = (await res.json()) as TokenPair;
        store.setTokens(data.access_token, data.refresh_token);
        return data.access_token;
      } catch {
        store.clear();
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  auth = true
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (auth) {
    let token = useAuthStore.getState().accessToken;
    if (!token) {
      token = await refreshAccessToken();
    }
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  let res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401 && auth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      res = await fetch(`${BASE}${path}`, { ...options, headers });
    }
  }

  const body = await parseJson(res);
  if (!res.ok) {
    throw new ApiClientError(res.status, body);
  }
  return body as T;
}

export const api = {
  get: <T>(path: string, auth = true) => apiFetch<T>(path, { method: "GET" }, auth),
  post: <T>(path: string, body?: unknown, auth = true) =>
    apiFetch<T>(
      path,
      { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined },
      auth
    ),
  patch: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  del: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
};

export { BASE as API_BASE };
