import { Link } from "react-router-dom";

import type { InvoiceListItem } from "@/api/invoices";
import { InvoiceRowStatusBadge } from "@/components/invoices/InvoiceStatusBadge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate, formatMoney } from "@/lib/format";

/** Invoices as a table on wide screens and cards on narrow ones. */
export function InvoiceList({ rows }: { rows: InvoiceListItem[] }) {
  return (
    <>
    <div className="hidden lg:block">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Invoice</TableHead>
            <TableHead>Client</TableHead>
            <TableHead>Issued / due</TableHead>
            <TableHead className="text-right">Total</TableHead>
            <TableHead className="text-right">Balance</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((invoice) => (
            <TableRow key={invoice.id}>
              <TableCell>
                <Link
                  to={`/invoices/${invoice.id}`}
                  className="font-medium underline-offset-4 hover:underline"
                >
                  {invoice.invoice_number}
                </Link>
                <p className="text-xs text-muted-foreground">
                  {invoice.reference || "No reference"}
                </p>
              </TableCell>
              <TableCell>
                <p>{invoice.client_name}</p>
                <p className="text-xs text-muted-foreground">
                  {invoice.client_email || "No billing email"}
                </p>
              </TableCell>
              <TableCell>
                <p>{formatDate(invoice.issue_date)}</p>
                <p className="text-xs text-muted-foreground">
                  due {formatDate(invoice.due_date)}
                </p>
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatMoney(invoice.total_amount)}
              </TableCell>
              <TableCell className="text-right font-medium tabular-nums">
                {formatMoney(invoice.balance_due)}
              </TableCell>
              <TableCell>
                <InvoiceRowStatusBadge invoice={invoice} />
                {invoice.status === "partially_paid" ? (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatMoney(invoice.amount_paid)} paid
                  </p>
                ) : null}
              </TableCell>
              <TableCell className="text-right">
                <Button asChild variant="outline" size="sm">
                  <Link to={`/invoices/${invoice.id}`}>Open</Link>
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>

    <ul className="space-y-3 lg:hidden">
      {rows.map((invoice) => (
        <li key={invoice.id} className="space-y-3 rounded-lg border p-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <Link
                to={`/invoices/${invoice.id}`}
                className="text-sm font-medium underline-offset-4 hover:underline"
              >
                {invoice.invoice_number}
              </Link>
              <p className="truncate text-xs text-muted-foreground">
                {invoice.client_name}
              </p>
            </div>
            <InvoiceRowStatusBadge invoice={invoice} />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>
              Issued {formatDate(invoice.issue_date)} · due{" "}
              {formatDate(invoice.due_date)}
            </span>
            <span className="font-medium text-foreground">
              {formatMoney(invoice.balance_due)} due
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground">
              Total {formatMoney(invoice.total_amount)}
            </span>
            <Button asChild variant="outline" size="sm">
              <Link to={`/invoices/${invoice.id}`}>Open invoice</Link>
            </Button>
          </div>
        </li>
      ))}
    </ul>
    </>
  );
}
