import type {
  Incident,
  IncidentCreateInput,
  IncidentListResponse,
  User,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Session lives entirely in cookies set by the backend (httpOnly JWT +
// readable CSRF token) — nothing to hold in JS. `credentials: "include"`
// is what makes the browser send/receive those cookies cross-origin;
// the CSRF cookie gets echoed back as a header on mutating requests
// (double-submit). See core/security.py for the server side.
function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  const method = (options.method ?? "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    const csrfToken = readCookie("csrf_token");
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(`${BASE_URL}/api/v1${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail ?? `Request failed (${response.status})`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function login(email: string, password: string): Promise<User> {
  return request<User>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
}

export function fetchMe(): Promise<User> {
  return request<User>("/auth/me");
}

export function listIncidents(params: {
  page?: number;
  pageSize?: number;
  severity?: string;
  status?: string;
} = {}): Promise<IncidentListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.pageSize) query.set("page_size", String(params.pageSize));
  if (params.severity) query.set("severity", params.severity);
  if (params.status) query.set("status", params.status);

  const queryString = query.toString();
  return request<IncidentListResponse>(`/incidents${queryString ? `?${queryString}` : ""}`);
}

export function createIncident(input: IncidentCreateInput): Promise<Incident> {
  return request<Incident>("/incidents", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateIncidentStatus(id: string, status: string): Promise<Incident> {
  return request<Incident>(`/incidents/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}
