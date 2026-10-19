/** Audit log types and TanStack Query hooks. */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { apiGet } from "@/api/client";
import type { Paginated } from "@/api/types";
import { toQueryString } from "@/lib/query";

export type AuditAction = "create" | "update" | "delete";

export type AuditEntry = {
  id: number;
  created_at: string;
  actor: number | null;
  actor_email: string | null;
  actor_label: string;
  action: AuditAction;
  action_label: string;
  model: string;
  model_label: string;
  object_id: string;
  summary: string;
  changes: Record<string, unknown>;
};

export type AuditActor = { id: number; email: string };

export type AuditFilters = {
  action?: AuditAction;
  model?: string;
  actor?: number;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
};

export const AUDIT_MODELS = [
  { value: "employees.employee", label: "Employee" },
  { value: "organization.team", label: "Team" },
  { value: "timeoff.leaverequest", label: "Leave request" },
  { value: "timeoff.leavetype", label: "Leave type" },
  { value: "employees.employeeinvite", label: "Employee invite" },
] as const;

export const auditKeys = {
  all: ["audit"] as const,
  list: (filters: AuditFilters) => ["audit", "list", filters] as const,
  actors: ["audit", "actors"] as const,
};

export function useAuditLogs(filters: AuditFilters = {}) {
  return useQuery({
    queryKey: auditKeys.list(filters),
    queryFn: () =>
      apiGet<Paginated<AuditEntry>>(`/audit-logs/${toQueryString(filters)}`),
    placeholderData: keepPreviousData,
  });
}

export function useAuditActors() {
  return useQuery({
    queryKey: auditKeys.actors,
    queryFn: () => apiGet<AuditActor[]>("/audit-logs/actors/"),
    staleTime: 60_000,
  });
}
