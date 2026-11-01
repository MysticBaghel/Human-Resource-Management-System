/** Invoice types and TanStack Query hooks. Components never fetch directly. */

import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  apiDelete,
  apiDownload,
  apiGet,
  apiPatch,
  apiPost,
  apiUpload,
} from "@/api/client";
import type { Paginated } from "@/api/types";
import { toQueryString, useInvalidatingMutation } from "@/lib/query";

export type InvoiceStatus =
  | "draft"
  | "sent"
  | "partially_paid"
  | "paid"
  | "cancelled";

export const INVOICE_STATUS_LABELS: Record<InvoiceStatus, string> = {
  draft: "Draft",
  sent: "Sent",
  partially_paid: "Partially paid",
  paid: "Paid",
  cancelled: "Cancelled",
};

export type InvoiceReminderTrigger = "manual" | "due_soon" | "overdue";

export type Client = {
  id: number;
  code: string;
  name: string;
  contact_name: string;
  email: string;
  phone: string;
  billing_address: string;
  tax_id: string;
  notes: string;
  is_active: boolean;
  invoice_count: number;
  created_at: string;
  updated_at: string;
};

export type ClientInput = {
  name: string;
  contact_name?: string;
  email?: string;
  phone?: string;
  billing_address?: string;
  tax_id?: string;
  notes?: string;
  is_active?: boolean;
};

export type InvoiceLineItem = {
  id: number;
  position: number;
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
};

export type InvoiceLineInput = {
  description: string;
  quantity: string;
  unit_price: string;
};

export type InvoicePaymentMethod =
  | "bank_transfer"
  | "upi"
  | "card"
  | "cheque"
  | "cash"
  | "other";

export const PAYMENT_METHOD_LABELS: Record<InvoicePaymentMethod, string> = {
  bank_transfer: "Bank transfer",
  upi: "UPI",
  card: "Card",
  cheque: "Cheque",
  cash: "Cash",
  other: "Other",
};

export type InvoicePayment = {
  id: number;
  invoice: number;
  amount: number;
  payment_date: string;
  method: InvoicePaymentMethod;
  method_label: string;
  reference: string;
  note: string;
  recorded_by: number | null;
  recorded_by_email: string | null;
  created_at: string;
};

export type InvoiceReminder = {
  id: number;
  invoice: number;
  recipient_email: string;
  subject: string;
  message: string;
  trigger: InvoiceReminderTrigger;
  trigger_label: string;
  provider: string;
  message_id: string;
  sent_by: number | null;
  sent_by_email: string | null;
  created_at: string;
};

export type InvoiceAttachmentKind = "original" | "signed" | "receipt" | "other";

export const ATTACHMENT_KIND_LABELS: Record<InvoiceAttachmentKind, string> = {
  original: "Original invoice",
  signed: "Signed copy",
  receipt: "Payment receipt",
  other: "Other",
};

export type InvoiceAttachment = {
  id: number;
  invoice: number;
  kind: InvoiceAttachmentKind;
  kind_label: string;
  title: string;
  original_name: string;
  content_type: string;
  size: number;
  download_path: string;
  uploaded_by: number | null;
  uploaded_by_email: string | null;
  created_at: string;
};

export type InvoiceListItem = {
  id: number;
  invoice_number: string;
  client: number;
  client_name: string;
  client_email: string;
  status: InvoiceStatus;
  status_label: string;
  issue_date: string;
  due_date: string;
  currency: string;
  reference: string;
  subtotal: number;
  discount_amount: number;
  tax_rate: number;
  tax_amount: number;
  total_amount: number;
  amount_paid: number;
  balance_due: number;
  is_overdue: boolean;
  days_overdue: number;
  reminder_due: boolean;
  can_send_reminder: boolean;
  can_record_payment: boolean;
  items_count: number;
  reminder_count: number;
  last_reminded_at: string | null;
  sent_at: string | null;
  sent_to: string;
  sent_via: string;
  sent_message_id: string;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
};

export type InvoiceDetail = InvoiceListItem & {
  client_contact_name: string;
  client_address: string;
  client_tax_id: string;
  notes: string;
  terms: string;
  cancelled_at: string | null;
  created_by: number | null;
  created_by_email: string | null;
  can_cancel: boolean;
  is_editable: boolean;
  items: InvoiceLineItem[];
  payments: InvoicePayment[];
  reminders: InvoiceReminder[];
  attachments: InvoiceAttachment[];
};

export type InvoiceInput = {
  client: number;
  issue_date: string;
  due_date: string;
  currency?: string;
  reference?: string;
  notes?: string;
  terms?: string;
  discount_amount: string;
  tax_rate: string;
  items: InvoiceLineInput[];
};

export type InvoiceDashboard = {
  as_of: string;
  active_clients: number;
  total_invoices: number;
  draft_count: number;
  outstanding_count: number;
  outstanding_amount: string;
  overdue_count: number;
  overdue_amount: string;
  due_soon_count: number;
  due_soon_amount: string;
  collected_this_month: string;
  payments_this_month: number;
  reminders_sent_this_month: number;
  reminder_queue_count: number;
  recent_invoices: InvoiceListItem[];
};

export type ReminderQueue = {
  as_of: string;
  days: number;
  cooldown_days: number;
  count: number;
  results: InvoiceListItem[];
};

export type InvoiceListFilters = {
  status?: InvoiceStatus | "overdue";
  overdue?: boolean;
  has_balance?: boolean;
  client?: number;
  search?: string;
  date_from?: string;
  date_to?: string;
  due_before?: string;
  page?: number;
  page_size?: number;
};

export type ClientFilters = {
  search?: string;
  active?: boolean;
  page?: number;
  page_size?: number;
};

export type PaymentInput = {
  amount: string;
  payment_date: string;
  method: InvoicePaymentMethod;
  reference?: string;
  note?: string;
};

export type ReminderInput = {
  recipient_email?: string;
  subject?: string;
  message?: string;
};

export type InvoiceSendInput = {
  recipient_email?: string;
  subject?: string;
  message?: string;
};

export const invoiceKeys = {
  all: ["invoices"] as const,
  dashboard: ["invoices", "dashboard"] as const,
  list: (filters: InvoiceListFilters) =>
    ["invoices", "list", filters] as const,
  detail: (id: number) => ["invoices", "detail", id] as const,
  queue: (days: number) => ["invoices", "queue", days] as const,
  clients: (filters: ClientFilters) =>
    ["invoices", "clients", filters] as const,
};

function useInvalidateInvoices() {
  const queryClient = useQueryClient();
  return () =>
    queryClient.invalidateQueries({ queryKey: invoiceKeys.all });
}

export function useInvoiceDashboard() {
  return useQuery({
    queryKey: invoiceKeys.dashboard,
    queryFn: () => apiGet<InvoiceDashboard>("/invoices/dashboard/"),
    staleTime: 0,
  });
}

export function useInvoices(filters: InvoiceListFilters = {}) {
  return useQuery({
    queryKey: invoiceKeys.list(filters),
    queryFn: () =>
      apiGet<Paginated<InvoiceListItem>>(
        `/invoices/${toQueryString(filters)}`,
      ),
    placeholderData: keepPreviousData,
  });
}

export function useInvoice(id: number | undefined) {
  return useQuery({
    queryKey: invoiceKeys.detail(id ?? 0),
    queryFn: () => apiGet<InvoiceDetail>(`/invoices/${id}/`),
    enabled: id !== undefined,
  });
}

export function useReminderQueue(days = 7) {
  return useQuery({
    queryKey: invoiceKeys.queue(days),
    queryFn: () =>
      apiGet<ReminderQueue>(`/invoices/reminder-queue/${toQueryString({ days })}`),
    staleTime: 0,
  });
}

export function useClients(filters: ClientFilters = {}) {
  return useQuery({
    queryKey: invoiceKeys.clients(filters),
    queryFn: () =>
      apiGet<Paginated<Client>>(`/clients/${toQueryString(filters)}`),
    placeholderData: keepPreviousData,
  });
}

export function useCreateClient() {
  const invalidate = useInvalidateInvoices();
  return useInvalidatingMutation(
    (input: ClientInput) => apiPost<Client>("/clients/", input),
    invalidate,
  );
}

export function useUpdateClient(id: number) {
  const invalidate = useInvalidateInvoices();
  return useInvalidatingMutation(
    (input: Partial<ClientInput>) =>
      apiPatch<Client>(`/clients/${id}/`, input),
    invalidate,
  );
}

export function useDeleteClient() {
  const invalidate = useInvalidateInvoices();
  return useInvalidatingMutation(
    (id: number) => apiDelete<void>(`/clients/${id}/`),
    invalidate,
  );
}

export function useCreateInvoice() {
  const invalidate = useInvalidateInvoices();
  return useInvalidatingMutation(
    (input: InvoiceInput) =>
      apiPost<InvoiceDetail>("/invoices/", input),
    invalidate,
  );
}

export function useUpdateInvoice(id: number) {
  const invalidate = useInvalidateInvoices();
  return useInvalidatingMutation(
    (input: InvoiceInput) =>
      apiPatch<InvoiceDetail>(`/invoices/${id}/`, input),
    invalidate,
  );
}

export function useSendInvoice() {
  const invalidate = useInvalidateInvoices();
  return useInvalidatingMutation(
    ({ id, ...input }: InvoiceSendInput & { id: number }) =>
      apiPost<InvoiceDetail>(`/invoices/${id}/send/`, input),
    invalidate,
  );
}

export function useCancelInvoice() {
  const invalidate = useInvalidateInvoices();
  return useInvalidatingMutation(
    (id: number) =>
      apiPost<InvoiceDetail>(`/invoices/${id}/cancel/`),
    invalidate,
  );
}

export function useRecordInvoicePayment() {
  const invalidate = useInvalidateInvoices();
  return useInvalidatingMutation(
    ({ id, ...input }: PaymentInput & { id: number }) =>
      apiPost<InvoiceDetail>(`/invoices/${id}/payment/`, input),
    invalidate,
  );
}

export function useSendInvoiceReminder() {
  const invalidate = useInvalidateInvoices();
  return useInvalidatingMutation(
    ({ id, ...input }: ReminderInput & { id: number }) =>
      apiPost<{ reminder: InvoiceReminder; invoice: InvoiceDetail }>(
        `/invoices/${id}/reminder/`,
        input,
      ),
    invalidate,
  );
}

export function useUploadInvoiceAttachment(invoiceId: number) {
  const invalidate = useInvalidateInvoices();
  return useInvalidatingMutation(
    ({
      file,
      kind,
      title,
    }: {
      file: File;
      kind: InvoiceAttachmentKind;
      title: string;
    }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("kind", kind);
      formData.append("title", title);
      return apiUpload<InvoiceAttachment>(
        `/invoices/${invoiceId}/attachments/`,
        formData,
      );
    },
    invalidate,
  );
}

export function useDeleteInvoiceAttachment(invoiceId: number) {
  const invalidate = useInvalidateInvoices();
  return useInvalidatingMutation(
    (attachmentId: number) =>
      apiDelete<void>(`/invoices/${invoiceId}/attachments/${attachmentId}/`),
    invalidate,
  );
}

export function downloadInvoicePdf(invoice: InvoiceListItem): Promise<void> {
  return apiDownload(
    `/invoices/${invoice.id}/pdf/`,
    `${invoice.invoice_number}.pdf`,
  );
}

export function downloadInvoiceAttachment(
  invoiceId: number,
  attachment: InvoiceAttachment,
): Promise<void> {
  return apiDownload(
    `/invoices/${invoiceId}/attachments/${attachment.id}/download/`,
    attachment.original_name,
  );
}
