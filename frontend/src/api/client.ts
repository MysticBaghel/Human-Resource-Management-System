/** Typed HTTP client for the HRMS API.
 *
 * Session auth needs the CSRF cookie echoed back in a header on unsafe
 * requests, and cookies must be sent, so every call goes through here.
 */

const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  status: number;
  code: string;
  fields: Record<string, string[]>;

  constructor(
    message: string,
    status: number,
    code = "error",
    fields: Record<string, string[]> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

function buildPath(path: string): string {
  return `${API_PREFIX}${path.startsWith("/") ? path : `/${path}`}`;
}

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : null;
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body } = options;

  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (method !== "GET") {
    const csrfToken = readCookie("csrftoken");
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }
  }

  const response = await fetch(buildPath(path), {
    method,
    headers,
    credentials: "include",
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const data = (payload ?? {}) as {
      detail?: string;
      code?: string;
      fields?: Record<string, string[]>;
    };
    throw new ApiError(
      data.detail ?? `Request failed with status ${response.status}.`,
      response.status,
      data.code,
      data.fields,
    );
  }

  return payload as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: body ?? {} });
}

export function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: "PATCH", body: body ?? {} });
}

/** Download a file (currently only PDF payslips) with the session cookie. */
export async function apiDownload(
  path: string,
  fallbackFilename: string,
): Promise<void> {
  const response = await fetch(buildPath(path), {
    headers: { Accept: "application/pdf" },
    credentials: "include",
  });

  if (!response.ok) {
    const text = await response.text();
    let payload: { detail?: string; code?: string; fields?: Record<string, string[]> } = {};
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = {};
      }
    }
    throw new ApiError(
      payload.detail ?? `Download failed with status ${response.status}.`,
      response.status,
      payload.code,
      payload.fields,
    );
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] ?? fallbackFilename;

  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

/** Ask Django to set the CSRF cookie before the first unsafe request. */
export function ensureCsrfCookie(): Promise<void> {
  return request<{ detail: string }>("/auth/csrf/").then(() => undefined);
}
