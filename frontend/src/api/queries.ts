/** TanStack Query bindings. Components never call fetch directly. */

import { useQuery } from "@tanstack/react-query";

import { apiGet, apiPost, ensureCsrfCookie } from "@/api/client";

export type HealthResponse = { status: string };

export type Role = "admin" | "hr" | "manager" | "employee";

export type User = {
  id: number;
  email: string;
  role: Role;
  is_active: boolean;
  date_joined: string;
};

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Admin",
  hr: "HR",
  manager: "Manager",
  employee: "Employee",
};

export const meQueryKey = ["me"] as const;

/** The signed-in user, or null when there is no valid session. */
export async function fetchMe(): Promise<User | null> {
  try {
    return await apiGet<User>("/auth/me/");
  } catch {
    // 401/403 simply means "not signed in"; the guards handle the redirect.
    return null;
  }
}

export function useMe() {
  return useQuery({
    queryKey: meQueryKey,
    queryFn: fetchMe,
    retry: false,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<HealthResponse>("/health/"),
    retry: 1,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function login(email: string, password: string): Promise<User> {
  return apiPost<User>("/auth/login/", { email, password });
}

export function logout(): Promise<void> {
  return apiPost<void>("/auth/logout/");
}

export function requestPasswordReset(email: string): Promise<{ detail: string }> {
  return apiPost<{ detail: string }>("/auth/password-reset/", { email });
}

export function confirmPasswordReset(
  uid: string,
  token: string,
  newPassword: string,
): Promise<{ detail: string }> {
  return apiPost<{ detail: string }>("/auth/password-reset/confirm/", {
    uid,
    token,
    new_password: newPassword,
  });
}

/** Set the first password from the link in the invite email. */
export function acceptInvite(token: string, password: string): Promise<User> {
  return apiPost<User>("/auth/accept-invite/", { token, password });
}

export { ensureCsrfCookie };
