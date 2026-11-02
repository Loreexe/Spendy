export type UserStatus = "pending" | "active" | "rejected" | "disabled";

export interface User {
  id: number;
  email: string | null;
  username: string | null;
  status: UserStatus;
  is_global_admin: boolean;
  date_joined: string;
}

export interface SetupStatus {
  setup_required: boolean;
  can_setup: boolean;
  client_is_private: boolean;
  registration_mode: "approval" | "open";
  admin_username: string;
}

export interface RegisterResult {
  user: User;
  pending: boolean;
  detail: string;
}

export interface Settings {
  registration_mode: "approval" | "open";
  setup_completed: boolean;
}

export class ApiError extends Error {
  status: number;
  code?: string;
  data: unknown;

  constructor(status: number, message: string, data: unknown, code?: string) {
    super(message);
    this.status = status;
    this.data = data;
    this.code = code;
  }
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : null;
}

async function ensureCsrf(): Promise<string> {
  let token = getCookie("csrftoken");
  if (!token) {
    await fetch("/api/auth/csrf/", { credentials: "include" });
    token = getCookie("csrftoken");
  }
  return token ?? "";
}

function firstError(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;
  for (const value of Object.values(data as Record<string, unknown>)) {
    if (typeof value === "string") return value;
    if (Array.isArray(value) && typeof value[0] === "string") return value[0];
    if (value && typeof value === "object") {
      const nested = firstError(value);
      if (nested) return nested;
    }
  }
  return null;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD") {
    const token = await ensureCsrf();
    if (token) headers.set("X-CSRFToken", token);
  }

  const response = await fetch(path, {
    ...options,
    method,
    headers,
    credentials: "include",
  });

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const record = (data ?? {}) as Record<string, unknown>;
    throw new ApiError(
      response.status,
      firstError(data) ?? "Operazione non riuscita.",
      data,
      typeof record.code === "string" ? record.code : undefined,
    );
  }

  return data as T;
}

export const api = {
  csrf: () => request("/api/auth/csrf/"),

  setupStatus: () => request<SetupStatus>("/api/auth/setup-status/"),

  setup: (password: string, passwordConfirm: string) =>
    request<{ user: User; setup_completed: boolean }>("/api/auth/setup/", {
      method: "POST",
      body: JSON.stringify({ password, password_confirm: passwordConfirm }),
    }),

  login: (identifier: string, password: string) =>
    request<{ user: User }>("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    }),

  logout: () =>
    request<{ detail: string }>("/api/auth/logout/", { method: "POST" }),

  me: () => request<{ user: User | null }>("/api/auth/me/"),

  updateEmail: (email: string) =>
    request<{ user: User }>("/api/auth/me/", {
      method: "PATCH",
      body: JSON.stringify({ email }),
    }),

  register: (email: string, password: string, passwordConfirm: string) =>
    request<RegisterResult>("/api/auth/register/", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        password_confirm: passwordConfirm,
      }),
    }),

  adminUsers: (status?: UserStatus) =>
    request<{ users: User[] }>(
      `/api/admin/users/${status ? `?status=${status}` : ""}`,
    ),

  adminDecision: (userId: number, decision: "approve" | "reject") =>
    request<{ user: User }>(`/api/admin/users/${userId}/${decision}/`, {
      method: "POST",
    }),

  adminSettings: () => request<Settings>("/api/admin/settings/"),

  updateSettings: (registrationMode: "approval" | "open") =>
    request<Settings>("/api/admin/settings/", {
      method: "PATCH",
      body: JSON.stringify({ registration_mode: registrationMode }),
    }),
};
