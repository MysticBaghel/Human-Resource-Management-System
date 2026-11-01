
/** Typed HTTP client for the HRMS API.
 * Supports Django session authentication and CSRF across separate Render origins.
 */

const API_PREFIX = "/api/v1";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

let csrfToken: string | null = null;
let csrfRequest: Promise<string> | null = null;

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
  return `${API_BASE_URL}${API_PREFIX}${path.startsWith("/") ? path : `/${path}`}`;
}

type ErrorPayload = {
  detail?: string;
  code?: string;
  fields?: Record<string, string[]>;
};

type CsrfResponse = {
  detail: string;
  csrfToken: string;
};

async function getCsrfToken(forceRefresh = false): Promise<string> {
  if (csrfToken && !forceRefresh) return csrfToken;
  if (csrfRequest && !forceRefresh) return csrfRequest;

  csrfRequest = (async () => {
    const response = await fetch(buildPath("/auth/csrf/"), {
      method: "GET",
      credentials: "include",
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new ApiError("Unable to obtain CSRF token.", response.status);
    }

    const data = (await response.json()) as CsrfResponse;

    if (!data.csrfToken) {
      throw new ApiError("Server did not return a CSRF token.", response.status);
    }

    csrfToken = data.csrfToken;
    return csrfToken;
  })();

  try {
    return await csrfRequest;
  } finally {
    csrfRequest = null;
  }
}

async function parseResponse<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
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
    const data = (payload ?? {}) as ErrorPayload;
    throw new ApiError(
      data.detail ?? fallbackMessage,
      response.status,
      data.code,
      data.fields,
    );
  }

  return payload as T;
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
};

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body } = options;

  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (method !== "GET") {
    headers["X-CSRFToken"] = await getCsrfToken();
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

  const result = await parseResponse<T>(
    response,
    `Request failed with status ${response.status}.`,
  );

  // Django rotates the CSRF secret after a successful login.
  if (path.includes("/auth/login/") && response.ok) {
    csrfToken = null;
  }

  return result;
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

export function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

/** Upload FormData with session and CSRF protection. */
export async function apiUpload<T>(
  path: string,
  formData: FormData,
): Promise<T> {
  const token = await getCsrfToken();

  const response = await fetch(buildPath(path), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "X-CSRFToken": token,
    },
    credentials: "include",
    body: formData,
  });

  return parseResponse<T>(
    response,
    `Upload failed with status ${response.status}.`,
  );
}

/** Download a file using the current session. */
export async function apiDownload(
  path: string,
  fallbackFilename: string,
): Promise<void> {
  const response = await fetch(buildPath(path), {
    headers: { Accept: "*/*" },
    credentials: "include",
  });

  if (!response.ok) {
    await parseResponse(response, `Download failed with status ${response.status}.`);
    return;
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

/** Fetch and cache the CSRF token before the first unsafe request. */
export async function ensureCsrfCookie(): Promise<void> {
  await getCsrfToken();
}
