/** Employee types and TanStack Query hooks. Components never fetch directly. */

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { apiGet, apiPatch, apiPost } from "@/api/client";
import type { Role } from "@/api/queries";
import type { Paginated } from "@/api/types";
import { toQueryString } from "@/lib/query";

export type EmploymentType = "full_time" | "part_time" | "contract" | "intern";
export type EmployeeStatus = "active" | "inactive";

export const EMPLOYMENT_TYPE_LABELS: Record<EmploymentType, string> = {
  full_time: "Full time",
  part_time: "Part time",
  contract: "Contract",
  intern: "Intern",
};

export const STATUS_LABELS: Record<EmployeeStatus, string> = {
  active: "Active",
  inactive: "Inactive",
};

export type Employee = {
  id: number;
  email: string;
  role: Role;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
  job_title: string;
  team: number | null;
  team_name: string | null;
  manager: number | null;
  manager_name: string | null;
  start_date: string;
  employment_type: EmploymentType;
  status: EmployeeStatus;
};

export type EmployeeInput = {
  email: string;
  role?: Role;
  first_name: string;
  last_name: string;
  phone?: string;
  job_title?: string;
  team?: number | null;
  manager?: number | null;
  start_date: string;
  employment_type?: EmploymentType;
};

export type EmployeeFilters = {
  search?: string;
  team?: number;
  status?: EmployeeStatus;
  role?: Role;
  page?: number;
  page_size?: number;
};

export const employeeKeys = {
  all: ["employees"] as const,
  list: (filters: EmployeeFilters) =>
    [...employeeKeys.all, "list", filters] as const,
  detail: (id: number) => [...employeeKeys.all, "detail", id] as const,
};

export function useEmployees(filters: EmployeeFilters = {}) {
  return useQuery({
    queryKey: employeeKeys.list(filters),
    queryFn: () =>
      apiGet<Paginated<Employee>>(`/employees/${toQueryString(filters)}`),
    placeholderData: keepPreviousData,
  });
}

export function useEmployee(id: number | undefined) {
  return useQuery({
    queryKey: employeeKeys.detail(id ?? 0),
    queryFn: () => apiGet<Employee>(`/employees/${id}/`),
    enabled: id !== undefined,
  });
}

export function useCreateEmployee() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: EmployeeInput) =>
      apiPost<Employee>("/employees/", input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: employeeKeys.all });
    },
  });
}

export function useUpdateEmployee(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: Partial<EmployeeInput>) =>
      apiPatch<Employee>(`/employees/${id}/`, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: employeeKeys.all });
    },
  });
}

export type EmployeeStatusAction = "deactivate" | "reactivate";

export function useSetEmployeeStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      action,
    }: {
      id: number;
      action: EmployeeStatusAction;
    }) => apiPost<Employee>(`/employees/${id}/${action}/`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: employeeKeys.all });
    },
  });
}
