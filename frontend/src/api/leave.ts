/** Leave types, balances, requests, preview and the team calendar. */

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { apiGet, apiPost } from "@/api/client";
import type { Paginated } from "@/api/types";
import { toQueryString } from "@/lib/query";

export type LeaveStatus = "pending" | "approved" | "rejected" | "cancelled";

export const LEAVE_STATUS_LABELS: Record<LeaveStatus, string> = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

export type LeaveType = {
  id: number;
  name: string;
  annual_days: number;
  is_paid: boolean;
  requires_approval: boolean;
  carry_over_max: number;
};

export type LeaveBalance = {
  id: number;
  employee: number;
  leave_type: number;
  leave_type_name: string;
  year: number;
  allocated: number;
  used: number;
  remaining: number;
};

export type LeaveRequest = {
  id: number;
  employee: number;
  employee_name: string;
  leave_type: number;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  half_day: boolean;
  days: number;
  status: LeaveStatus;
  reviewer: number | null;
  reviewer_name: string | null;
  review_comment: string;
  reviewed_at: string | null;
  created_at: string;
};

export type LeavePreview = {
  days: number;
  remaining: number | null;
  sufficient: boolean;
  overlap: boolean;
};

export type CalendarLeave = {
  id: number;
  employee: number;
  employee_name: string;
  leave_type: number;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  half_day: boolean;
};

export type CalendarHoliday = { id: number; date: string; name: string };

export type CalendarResponse = {
  year: number;
  month: number;
  results: CalendarLeave[];
  holidays: CalendarHoliday[];
};

export type LeaveRequestInput = {
  leave_type: number;
  start_date: string;
  end_date: string;
  half_day?: boolean;
};

export type LeaveRequestFilters = {
  status?: LeaveStatus;
  leave_type?: number;
  employee?: number;
  mine?: boolean;
  year?: number;
  page?: number;
  page_size?: number;
};

export const leaveKeys = {
  all: ["leave"] as const,
  types: ["leave", "types"] as const,
  balances: (year: number, employee?: number) =>
    ["leave", "balances", year, employee ?? null] as const,
  requests: (filters: LeaveRequestFilters) =>
    ["leave", "requests", filters] as const,
  preview: (input: LeaveRequestInput | null) =>
    ["leave", "preview", input] as const,
  calendar: (year: number, month: number) =>
    ["leave", "calendar", year, month] as const,
};

export function useLeaveTypes() {
  return useQuery({
    queryKey: leaveKeys.types,
    queryFn: () =>
      apiGet<Paginated<LeaveType>>(
        `/leave-types/${toQueryString({ page_size: 100 })}`,
      ),
    staleTime: 5 * 60_000,
  });
}

export function useLeaveBalances(year: number, employee?: number) {
  return useQuery({
    queryKey: leaveKeys.balances(year, employee),
    queryFn: () =>
      apiGet<Paginated<LeaveBalance>>(
        `/leave-balances/${toQueryString({ year, employee, page_size: 100 })}`,
      ),
  });
}

export function useLeaveRequests(filters: LeaveRequestFilters = {}) {
  return useQuery({
    queryKey: leaveKeys.requests(filters),
    queryFn: () =>
      apiGet<Paginated<LeaveRequest>>(
        `/leave-requests/${toQueryString(filters)}`,
      ),
    placeholderData: keepPreviousData,
  });
}

export function useLeavePreview(input: LeaveRequestInput | null) {
  return useQuery({
    queryKey: leaveKeys.preview(input),
    queryFn: () =>
      apiPost<LeavePreview>("/leave-requests/preview/", input ?? {}),
    enabled: input !== null,
    retry: false,
    staleTime: 0,
  });
}

export function useCalendar(year: number, month: number) {
  return useQuery({
    queryKey: leaveKeys.calendar(year, month),
    queryFn: () =>
      apiGet<CalendarResponse>(
        `/leave-calendar/${toQueryString({ year, month })}`,
      ),
  });
}

function useInvalidateLeave() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: leaveKeys.all });
}

export function useCreateLeaveRequest() {
  const invalidate = useInvalidateLeave();
  return useMutation({
    mutationFn: (input: LeaveRequestInput) =>
      apiPost<LeaveRequest>("/leave-requests/", input),
    onSuccess: () => {
      void invalidate();
    },
  });
}

export function useReviewLeaveRequest() {
  const invalidate = useInvalidateLeave();
  return useMutation({
    mutationFn: ({
      id,
      action,
      comment,
    }: {
      id: number;
      action: "approve" | "reject";
      comment: string;
    }) =>
      apiPost<LeaveRequest>(`/leave-requests/${id}/${action}/`, { comment }),
    onSuccess: () => {
      void invalidate();
    },
  });
}

export function useCancelLeaveRequest() {
  const invalidate = useInvalidateLeave();
  return useMutation({
    mutationFn: (id: number) =>
      apiPost<LeaveRequest>(`/leave-requests/${id}/cancel/`),
    onSuccess: () => {
      void invalidate();
    },
  });
}
