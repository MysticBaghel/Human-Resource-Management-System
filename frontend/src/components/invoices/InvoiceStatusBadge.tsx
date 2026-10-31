import { Badge } from "@/components/ui/badge";
import {
  INVOICE_STATUS_LABELS,
  type InvoiceListItem,
  type InvoiceStatus,
} from "@/api/invoices";

type InvoiceStatusBadgeProps = {
  status: InvoiceStatus;
  is_overdue?: boolean;
};

/** Overdue is derived from the due date, not stored as a separate status. */
export function InvoiceStatusBadge({
  status,
  is_overdue = false,
}: InvoiceStatusBadgeProps) {
  if (is_overdue) return <Badge variant="destructive">Overdue</Badge>;

  const variant =
    status === "paid"
      ? "success"
      : status === "partially_paid"
        ? "default"
        : status === "cancelled"
          ? "outline"
          : "secondary";

  return <Badge variant={variant}>{INVOICE_STATUS_LABELS[status]}</Badge>;
}

export function InvoiceRowStatusBadge({ invoice }: { invoice: InvoiceListItem }) {
  return (
    <InvoiceStatusBadge status={invoice.status} is_overdue={invoice.is_overdue} />
  );
}
