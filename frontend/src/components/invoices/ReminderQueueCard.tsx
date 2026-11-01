import { Send } from "lucide-react";
import { Link } from "react-router-dom";

import type { InvoiceListItem } from "@/api/invoices";
import { InvoiceRowStatusBadge } from "@/components/invoices/InvoiceStatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate, formatMoney } from "@/lib/format";

type ReminderQueueCardProps = {
  queueRows: InvoiceListItem[];
  onReviewOverdue: () => void;
};

/** Invoices that are due soon or overdue and outside the reminder cooldown. */
export function ReminderQueueCard({ queueRows, onReviewOverdue }: ReminderQueueCardProps) {
  return (
    <Card className="border-amber-200 bg-amber-50/40">
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 pb-3">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-base">
            <Send className="h-4 w-4" aria-hidden="true" />
            Payment reminders waiting
          </CardTitle>
          <CardDescription>
            {queueRows.length} invoice{queueRows.length === 1 ? "" : "s"} due
            soon or overdue, outside the reminder cooldown.
          </CardDescription>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onReviewOverdue()}
        >
          Review overdue
        </Button>
      </CardHeader>
      <CardContent>
        <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {queueRows.slice(0, 3).map((invoice) => (
            <li
              key={invoice.id}
              className="rounded-lg border bg-background p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <Link
                    to={`/invoices/${invoice.id}`}
                    className="truncate text-sm font-medium underline-offset-4 hover:underline"
                  >
                    {invoice.invoice_number}
                  </Link>
                  <p className="truncate text-xs text-muted-foreground">
                    {invoice.client_name}
                  </p>
                </div>
                <InvoiceRowStatusBadge invoice={invoice} />
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                {formatMoney(invoice.balance_due)} due{" "}
                {formatDate(invoice.due_date)}
              </p>
              <Button asChild variant="ghost" size="sm" className="mt-2 px-0">
                <Link to={`/invoices/${invoice.id}?remind=1`}>
                  Send reminder
                </Link>
              </Button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
