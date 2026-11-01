import { MetricCard } from "@/components/common/MetricCard";
import type { InvoiceDetail } from "@/api/invoices";
import { formatDate, formatDateTime, formatMoney } from "@/lib/format";

type InvoiceMetricsProps = { invoice: InvoiceDetail };

export function InvoiceMetrics({ invoice }: InvoiceMetricsProps) {
  return (
  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
    <MetricCard
      label="Invoice total"
      value={formatMoney(invoice.total_amount)}
      hint={`${invoice.items.length} line item${
        invoice.items.length === 1 ? "" : "s"
      }`}
    />
    <MetricCard
      label="Amount paid"
      value={formatMoney(invoice.amount_paid)}
      hint={
        invoice.status === "partially_paid"
          ? "Partially paid"
          : invoice.status === "paid"
            ? "Paid in full"
            : "No payment recorded"
      }
    />
    <MetricCard
      label="Balance due"
      value={formatMoney(invoice.balance_due)}
      hint={invoice.is_overdue ? "Overdue" : `Due ${formatDate(invoice.due_date)}`}
    />
    <MetricCard
      label="Reminders"
      value={invoice.reminder_count}
      hint={
        invoice.last_reminded_at
          ? `Last sent ${formatDateTime(invoice.last_reminded_at)}`
          : "None sent yet"
      }
    />
  </div>
  );
}
