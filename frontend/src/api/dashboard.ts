/** The role-scoped dashboard payload. */

import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/api/client";
import type { AuditEntry } from "@/api/audit";
import type { LeaveBalance, LeaveRequest } from "@/api/leave";
import type { Role } from "@/api/queries";

export type DashboardData = {
  role: Role;
  metrics: Record<string, number>;
  recent_activity?: AuditEntry[];
  recent_employee_changes?: AuditEntry[];
  pending_requests?: LeaveRequest[];
  upcoming_leave?: LeaveRequest[];
  balances?: LeaveBalance[];
  recent_decisions?: LeaveRequest[];
};

export const dashboardKey = ["dashboard"] as const;

export function useDashboard() {
  return useQuery({
    queryKey: dashboardKey,
    queryFn: () => apiGet<DashboardData>("/dashboard/"),
    staleTime: 0,
  });
}
