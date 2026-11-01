/** Payroll types and TanStack Query hooks. Components never fetch directly. */

import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { apiDownload, apiGet, apiPatch, apiPost } from "@/api/client";
import type { Paginated } from "@/api/types";
import { toQueryString, useInvalidatingMutation } from "@/lib/query";

export type PayrollStatus = "draft" | "finalized";
export type PaymentStatus = "pending" | "paid" | "failed" | "cancelled";

export const PAYROLL_STATUS_LABELS: Record<PayrollStatus, string> = {
  draft: "Draft",
  finalized: "Finalized",
};

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  pending: "Pending",
  paid: "Paid",
  failed: "Failed",
  cancelled: "Cancelled",
};

export { MONTH_NAMES } from "@/lib/date";

/** Money fields shared by a salary structure and a payroll snapshot. */
export type SalaryValues = {
  basic_salary: number;
  hra: number;
  conveyance_allowance: number;
  medical_allowance: number;
  special_allowance: number;
  other_allowances: number;
  provident_fund: number;
  professional_tax: number;
  income_tax: number;
  other_deductions: number;
  gross_salary: number;
  total_deductions: number;
  net_salary: number;
};

export type SalaryStructure = SalaryValues & {
  id: number;
  employee: number;
  employee_name: string;
  employee_code: string;
  email: string;
  designation: string;
  department: string | null;
  date_of_joining: string;
  effective_date: string;
  is_active: boolean;
  revoked_at: string | null;
  created_by: number | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
};

export type SalaryStructureInput = {
  employee: number;
  basic_salary: string;
  hra: string;
  conveyance_allowance: string;
  medical_allowance: string;
  special_allowance: string;
  other_allowances: string;
  provident_fund: string;
  professional_tax: string;
  income_tax: string;
  other_deductions: string;
  effective_date: string;
  reason?: string;
};

export type SalarySnapshot = {
  basic_salary: string;
  hra: string;
  conveyance_allowance: string;
  medical_allowance: string;
  special_allowance: string;
  other_allowances: string;
  provident_fund: string;
  professional_tax: string;
  income_tax: string;
  other_deductions: string;
  gross_salary: string;
  total_deductions: string;
  net_salary: string;
  effective_date: string;
  is_active: boolean;
};

export type SalaryRevision = {
  id: number;
  employee: number;
  employee_name: string;
  previous_structure: number | null;
  new_structure: number | null;
  previous_values: SalarySnapshot;
  new_values: SalarySnapshot;
  effective_date: string;
  updated_by: number | null;
  updated_by_email: string | null;
  reason: string;
  created_at: string;
};

export type PayrollRecord = SalaryValues & {
  id: number;
  employee: number;
  employee_name: string;
  employee_code: string;
  designation: string;
  department: string;
  date_of_joining: string;
  payroll_month: number;
  payroll_year: number;
  pay_period: string;
  payslip_number: string;
  adjustment_amount: number;
  adjustment_note: string;
  adjusted_gross: number;
  status: PayrollStatus;
  payment_status: PaymentStatus;
  payment_date: string | null;
  payment_reference: string;
  generated_by: number | null;
  generated_by_email: string | null;
  finalized_by: number | null;
  finalized_by_email: string | null;
  finalized_at: string | null;
  created_at: string;
  updated_at: string;
};

export type PayrollDashboard = {
  month: number;
  year: number;
  as_of: string;
  employees_with_salary_structures: number;
  current_month_payroll_total: string;
  total_paid_amount: string;
  pending_payments_count: number;
  pending_payments_amount: string;
  failed_payments_count: number;
  draft_count: number;
  finalized_count: number;
  recent_activity: PayrollRecord[];
};

export type PayrollGenerationResult = {
  generated_count: number;
  skipped_count: number;
  generated: PayrollRecord[];
  skipped: { employee: number; employee_name: string; reason: string }[];
};

export type SalaryStructureFilters = {
  mine?: boolean;
  employee?: number;
  active?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
};

export type PayrollRecordFilters = {
  mine?: boolean;
  year?: number;
  month?: number;
  status?: PayrollStatus;
  payment_status?: PaymentStatus;
  employee?: number;
  search?: string;
  page?: number;
  page_size?: number;
};

export const payrollKeys = {
  all: ["payroll"] as const,
  dashboard: ["payroll", "dashboard"] as const,
  structures: (filters: SalaryStructureFilters) =>
    ["payroll", "structures", filters] as const,
  revisions: (employee: number) =>
    ["payroll", "revisions", employee] as const,
  records: (filters: PayrollRecordFilters) =>
    ["payroll", "records", filters] as const,
};

export const EARNING_FIELDS = [
  "basic_salary",
  "hra",
  "conveyance_allowance",
  "medical_allowance",
  "special_allowance",
  "other_allowances",
] as const;

export const DEDUCTION_FIELDS = [
  "provident_fund",
  "professional_tax",
  "income_tax",
  "other_deductions",
] as const;

export const EARNING_LABELS: Record<(typeof EARNING_FIELDS)[number], string> = {
  basic_salary: "Basic salary",
  hra: "House rent allowance (HRA)",
  conveyance_allowance: "Conveyance allowance",
  medical_allowance: "Medical allowance",
  special_allowance: "Special allowance",
  other_allowances: "Other allowances",
};

export const DEDUCTION_LABELS: Record<
  (typeof DEDUCTION_FIELDS)[number],
  string
> = {
  provident_fund: "Provident fund (PF)",
  professional_tax: "Professional tax",
  income_tax: "Income tax / TDS",
  other_deductions: "Other deductions",
};

export function usePayrollDashboard() {
  return useQuery({
    queryKey: payrollKeys.dashboard,
    queryFn: () => apiGet<PayrollDashboard>("/payroll/dashboard/"),
    staleTime: 0,
  });
}

export function useSalaryStructures(filters: SalaryStructureFilters = {}) {
  return useQuery({
    queryKey: payrollKeys.structures(filters),
    queryFn: () =>
      apiGet<Paginated<SalaryStructure>>(
        `/payroll/salary-structures/${toQueryString(filters)}`,
      ),
    placeholderData: keepPreviousData,
  });
}

export function useSalaryRevisions(employee: number | undefined) {
  return useQuery({
    queryKey: payrollKeys.revisions(employee ?? 0),
    queryFn: () =>
      apiGet<Paginated<SalaryRevision>>(
        `/payroll/salary-revisions/${toQueryString({
          employee,
          page_size: 100,
        })}`,
      ),
    enabled: employee !== undefined,
  });
}

export function usePayrollRecords(filters: PayrollRecordFilters = {}) {
  return useQuery({
    queryKey: payrollKeys.records(filters),
    queryFn: () =>
      apiGet<Paginated<PayrollRecord>>(
        `/payroll/records/${toQueryString(filters)}`,
      ),
    placeholderData: keepPreviousData,
  });
}

function useInvalidatePayroll() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: payrollKeys.all });
}

export function useCreateSalaryStructure() {
  const invalidate = useInvalidatePayroll();
  return useInvalidatingMutation(
    (input: SalaryStructureInput) =>
      apiPost<SalaryStructure>("/payroll/salary-structures/", input),
    invalidate,
  );
}

export function useUpdateSalaryStructure(id: number) {
  const invalidate = useInvalidatePayroll();
  return useInvalidatingMutation(
    (input: SalaryStructureInput) =>
      apiPatch<SalaryStructure>(`/payroll/salary-structures/${id}/`, input),
    invalidate,
  );
}

/** Retire the active structure. Revision history and payroll snapshots stay. */
export function useRevokeSalaryStructure() {
  const invalidate = useInvalidatePayroll();
  return useInvalidatingMutation(
    (id: number) =>
      apiPost<SalaryStructure>(`/payroll/salary-structures/${id}/revoke/`),
    invalidate,
  );
}

export function useGeneratePayroll() {
  const invalidate = useInvalidatePayroll();
  return useInvalidatingMutation(
    (input: { month: number; year: number; employee?: number }) =>
      apiPost<PayrollGenerationResult>("/payroll/records/generate/", input),
    invalidate,
  );
}

export function useAdjustPayroll() {
  const invalidate = useInvalidatePayroll();
  return useInvalidatingMutation(
    ({
      id,
      adjustment_amount,
      adjustment_note,
    }: {
      id: number;
      adjustment_amount: number;
      adjustment_note: string;
    }) =>
      apiPatch<PayrollRecord>(`/payroll/records/${id}/`, {
        adjustment_amount: adjustment_amount.toFixed(2),
        adjustment_note,
      }),
    invalidate,
  );
}

export function useFinalizePayroll() {
  const invalidate = useInvalidatePayroll();
  return useInvalidatingMutation(
    (id: number) =>
      apiPost<PayrollRecord>(`/payroll/records/${id}/finalize/`),
    invalidate,
  );
}

/**
 * Cancel a payroll record. A draft is deleted (204, no body) so it can be
 * generated again; a finalized record comes back with payment_status
 * "cancelled" and is kept for audit.
 */
export function useCancelPayroll() {
  const invalidate = useInvalidatePayroll();
  return useInvalidatingMutation(
    (id: number) =>
      apiPost<PayrollRecord | void>(`/payroll/records/${id}/cancel/`),
    invalidate,
  );
}

export function useFinalizePayrollPeriod() {
  const invalidate = useInvalidatePayroll();
  return useInvalidatingMutation(
    (input: { month: number; year: number }) =>
      apiPost<{ finalized_count: number; records: PayrollRecord[] }>(
        "/payroll/records/finalize-period/",
        input,
      ),
    invalidate,
  );
}

export function useUpdatePayment() {
  const invalidate = useInvalidatePayroll();
  return useInvalidatingMutation(
    ({
      id,
      ...input
    }: {
      id: number;
      payment_status: PaymentStatus;
      payment_date: string | null;
      payment_reference: string;
    }) => apiPost<PayrollRecord>(`/payroll/records/${id}/payment/`, input),
    invalidate,
  );
}

export function downloadPayslip(record: PayrollRecord): Promise<void> {
  return apiDownload(
    `/payroll/records/${record.id}/payslip/`,
    `payslip-${record.payslip_number}.pdf`,
  );
}
