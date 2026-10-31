/** One invoice: line items, payments, reminders, uploads and PDF. */

import {
  ArrowLeft,
  Ban,
  Bell,
  Download,
  FileText,
  Paperclip,
  Pencil,
  Send,
  Trash2,
  Upload,
  Wallet,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import {
  downloadInvoiceAttachment,
  downloadInvoicePdf,
  useCancelInvoice,
  useDeleteInvoiceAttachment,
  useClients,
  useInvoice,
  type InvoiceAttachment,
} from "@/api/invoices";
import { EmptyState, ErrorState } from "@/components/common/states";
import { MetricCard } from "@/components/common/MetricCard";
import { InvoiceFormDialog } from "@/components/invoices/InvoiceFormDialog";
import { InvoiceStatusBadge } from "@/components/invoices/InvoiceStatusBadge";
import { InvoiceTotals } from "@/components/invoices/InvoiceTotals";
import { RecordPaymentDialog } from "@/components/invoices/RecordPaymentDialog";
import { SendInvoiceDialog } from "@/components/invoices/SendInvoiceDialog";
import { SendReminderDialog } from "@/components/invoices/SendReminderDialog";
import { UploadInvoiceDialog } from "@/components/invoices/UploadInvoiceDialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "@/components/ui/toast";
import { formatDate, formatDateTime, formatMoney } from "@/lib/format";

function PageSkeleton() {
  return (
    <div className="mx-auto w-full max-w-7xl space-y-6" aria-busy="true">
      <Skeleton className="h-8 w-64" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-28 w-full" />
        ))}
      </div>
      <Skeleton className="h-96 w-full" />
    </div>
  );
}

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(0)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function InvoiceDetailPage() {
  const { id } = useParams();
  const invoiceId = Number(id);
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: invoice, isLoading, isError, error, refetch } = useInvoice(
    Number.isFinite(invoiceId) ? invoiceId : undefined,
  );

  const clients = useClients({ page_size: 100 });
  const cancelMutation = useCancelInvoice();
  const deleteAttachment = useDeleteInvoiceAttachment(invoiceId);

  const [editOpen, setEditOpen] = useState(false);
  const [sendOpen, setSendOpen] = useState(false);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [reminderOpen, setReminderOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<InvoiceAttachment | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    if (!invoice) return;
    if (searchParams.get("remind") === "1") {
      setReminderOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete("remind");
      setSearchParams(next, { replace: true });
    }
  }, [invoice, searchParams, setSearchParams]);

  if (isLoading) return <PageSkeleton />;

  if (isError || invoice === undefined) {
    return (
      <div className="mx-auto w-full max-w-7xl space-y-6">
        <Button asChild variant="ghost" size="sm" className="px-0">
          <Link to="/invoices">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            All invoices
          </Link>
        </Button>
        <ErrorState
          title="Could not load this invoice"
          message={error instanceof Error ? error.message : undefined}
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const current = invoice;
  const isOutstanding = current.can_record_payment;

  async function handleCancel() {
    try {
      await cancelMutation.mutateAsync(current.id);
      setCancelOpen(false);
      toast({
        title: "Invoice cancelled",
        description: current.invoice_number,
        variant: "success",
      });
    } catch (caught) {
      toast({
        title: "Could not cancel the invoice",
        description: caught instanceof ApiError ? caught.message : "Please try again.",
        variant: "destructive",
      });
    }
  }

  async function handlePdf() {
    setDownloading("pdf");
    try {
      await downloadInvoicePdf(current);
    } catch (caught) {
      toast({
        title: "Could not download the invoice",
        description: caught instanceof ApiError ? caught.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setDownloading(null);
    }
  }

  async function handleAttachment(attachment: InvoiceAttachment) {
    setDownloading(`attachment-${attachment.id}`);
    try {
      await downloadInvoiceAttachment(current.id, attachment);
    } catch (caught) {
      toast({
        title: "Could not download the file",
        description: caught instanceof ApiError ? caught.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setDownloading(null);
    }
  }

  async function handleRemoveAttachment() {
    if (!removeTarget) return;
    try {
      await deleteAttachment.mutateAsync(removeTarget.id);
      setRemoveTarget(null);
      toast({ title: "File removed", variant: "success" });
    } catch (caught) {
      toast({
        title: "Could not remove the file",
        description: caught instanceof ApiError ? caught.message : "Please try again.",
        variant: "destructive",
      });
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <div className="space-y-2">
        <Button asChild variant="ghost" size="sm" className="px-0">
          <Link to="/invoices">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            All invoices
          </Link>
        </Button>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">
                {current.invoice_number}
              </h1>
              <InvoiceStatusBadge
                status={current.status}
                is_overdue={current.is_overdue}
              />
            </div>
            <p className="text-sm text-muted-foreground">
              {current.client_name} · issued {formatDate(current.issue_date)} ·
              due {formatDate(current.due_date)}
              {current.is_overdue
                ? ` · ${current.days_overdue} day${
                    current.days_overdue === 1 ? "" : "s"
                  } overdue`
                : ""}
            </p>
            {current.reference ? (
              <p className="text-xs text-muted-foreground">
                Reference: {current.reference}
              </p>
            ) : null}
            {current.sent_at ? (
              <p className="text-xs text-muted-foreground">
                Sent {formatDateTime(current.sent_at)}
                {current.sent_to ? ` to ${current.sent_to}` : ""}
                {current.sent_via === "gmail"
                  ? " via Gmail"
                  : current.sent_via === "django"
                    ? " via email"
                    : ""}
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-2">
            {current.is_editable ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditOpen(true)}
              >
                <Pencil className="h-4 w-4" aria-hidden="true" />
                Edit
              </Button>
            ) : null}
            {current.status === "draft" ? (
              <Button type="button" onClick={() => setSendOpen(true)}>
                <Send className="h-4 w-4" aria-hidden="true" />
                Send invoice
              </Button>
            ) : null}
            {isOutstanding ? (
              <>
                <Button
                  type="button"
                  onClick={() => setPaymentOpen(true)}
                  variant="outline"
                >
                  <Wallet className="h-4 w-4" aria-hidden="true" />
                  Record payment
                </Button>
                <Button
                  type="button"
                  onClick={() => setReminderOpen(true)}
                  variant="outline"
                >
                  <Bell className="h-4 w-4" aria-hidden="true" />
                  Send reminder
                </Button>
              </>
            ) : null}
            <Button
              type="button"
              variant="outline"
              onClick={() => void handlePdf()}
              disabled={downloading === "pdf"}
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              {downloading === "pdf" ? "Preparing…" : "PDF"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setUploadOpen(true)}
            >
              <Upload className="h-4 w-4" aria-hidden="true" />
              Upload
            </Button>
            {current.can_cancel ? (
              <Button
                type="button"
                variant="ghost"
                className="text-destructive hover:text-destructive"
                onClick={() => setCancelOpen(true)}
              >
                <Ban className="h-4 w-4" aria-hidden="true" />
                Cancel
              </Button>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Invoice total"
          value={formatMoney(current.total_amount)}
          hint={`${current.items.length} line item${
            current.items.length === 1 ? "" : "s"
          }`}
        />
        <MetricCard
          label="Amount paid"
          value={formatMoney(current.amount_paid)}
          hint={
            current.status === "partially_paid"
              ? "Partially paid"
              : current.status === "paid"
                ? "Paid in full"
                : "No payment recorded"
          }
        />
        <MetricCard
          label="Balance due"
          value={formatMoney(current.balance_due)}
          hint={current.is_overdue ? "Overdue" : `Due ${formatDate(current.due_date)}`}
        />
        <MetricCard
          label="Reminders"
          value={current.reminder_count}
          hint={
            current.last_reminded_at
              ? `Last sent ${formatDateTime(current.last_reminded_at)}`
              : "None sent yet"
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Line items</CardTitle>
              <CardDescription>
                Every amount is snapshotted on the invoice.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="hidden sm:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Description</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">Rate</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {current.items.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-medium">
                          {item.description}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {item.quantity}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(item.unit_price)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(item.amount)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <ul className="space-y-2 sm:hidden">
                {current.items.map((item) => (
                  <li
                    key={item.id}
                    className="flex items-start justify-between gap-3 rounded-lg border p-3"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{item.description}</p>
                      <p className="text-xs text-muted-foreground">
                        {item.quantity} × {formatMoney(item.unit_price)}
                      </p>
                    </div>
                    <p className="shrink-0 text-sm font-medium tabular-nums">
                      {formatMoney(item.amount)}
                    </p>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
              <div className="space-y-1">
                <CardTitle className="text-base">Payments</CardTitle>
                <CardDescription>
                  Recorded receipts. A partial payment keeps the invoice open.
                </CardDescription>
              </div>
              {isOutstanding ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setPaymentOpen(true)}
                >
                  Record payment
                </Button>
              ) : null}
            </CardHeader>
            <CardContent>
              {current.payments.length === 0 ? (
                <EmptyState
                  title="No payments recorded"
                  description="When money is received, record it here to keep the balance accurate."
                />
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Method</TableHead>
                        <TableHead>Reference</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {current.payments.map((payment) => (
                        <TableRow key={payment.id}>
                          <TableCell>{formatDate(payment.payment_date)}</TableCell>
                          <TableCell>{payment.method_label}</TableCell>
                          <TableCell>
                            {payment.reference || "—"}
                            {payment.note ? (
                              <p className="text-xs text-muted-foreground">
                                {payment.note}
                              </p>
                            ) : null}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatMoney(payment.amount)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
              <div className="space-y-1">
                <CardTitle className="text-base">Payment reminders</CardTitle>
                <CardDescription>
                  Reminder emails sent for this invoice, with their message.
                </CardDescription>
              </div>
              {isOutstanding ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setReminderOpen(true)}
                >
                  <Bell className="h-4 w-4" aria-hidden="true" />
                  Send reminder
                </Button>
              ) : null}
            </CardHeader>
            <CardContent>
              {current.reminders.length === 0 ? (
                <EmptyState
                  title="No reminders sent"
                  description="Send a reminder when the invoice is due or overdue."
                />
              ) : (
                <ul className="space-y-2">
                  {current.reminders.map((reminder) => (
                    <li key={reminder.id} className="rounded-lg border p-3">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-sm font-medium">
                            {reminder.subject}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            To {reminder.recipient_email} ·{" "}
                            {formatDateTime(reminder.created_at)}
                            {reminder.provider === "gmail" ? " · Gmail" : ""}
                          </p>
                        </div>
                        <span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
                          {reminder.trigger_label}
                        </span>
                      </div>
                      <details className="mt-2 text-xs text-muted-foreground">
                        <summary className="cursor-pointer select-none">
                          View message
                        </summary>
                        <pre className="mt-2 whitespace-pre-wrap font-sans">
                          {reminder.message}
                        </pre>
                      </details>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
              <div className="space-y-1">
                <CardTitle className="text-base">Uploaded files</CardTitle>
                <CardDescription>
                  Scanned invoice, signed copy, receipt or supporting document.
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setUploadOpen(true)}
              >
                <Upload className="h-4 w-4" aria-hidden="true" />
                Upload
              </Button>
            </CardHeader>
            <CardContent>
              {current.attachments.length === 0 ? (
                <EmptyState
                  title="No files uploaded"
                  description="Upload the original invoice or a signed copy as a PDF or image."
                  action={
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setUploadOpen(true)}
                    >
                      Upload a file
                    </Button>
                  }
                />
              ) : (
                <ul className="space-y-2">
                  {current.attachments.map((attachment) => (
                    <li
                      key={attachment.id}
                      className="flex flex-col gap-2 rounded-lg border p-3 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="flex min-w-0 items-start gap-2">
                        <Paperclip
                          className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                          aria-hidden="true"
                        />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">
                            {attachment.title || attachment.original_name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {attachment.kind_label} ·{" "}
                            {formatBytes(attachment.size)} ·{" "}
                            {formatDateTime(attachment.created_at)}
                            {attachment.uploaded_by_email
                              ? ` · ${attachment.uploaded_by_email}`
                              : ""}
                          </p>
                        </div>
                      </div>
                      <div className="flex gap-1 sm:shrink-0">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => void handleAttachment(attachment)}
                          disabled={downloading === `attachment-${attachment.id}`}
                        >
                          <Download className="h-4 w-4" aria-hidden="true" />
                          {downloading === `attachment-${attachment.id}`
                            ? "…"
                            : "Download"}
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-9 w-9 text-muted-foreground"
                          onClick={() => setRemoveTarget(attachment)}
                          aria-label={`Remove ${attachment.original_name}`}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Totals</CardTitle>
            </CardHeader>
            <CardContent>
              <InvoiceTotals
                subtotal={current.subtotal}
                discount_amount={current.discount_amount}
                tax_rate={current.tax_rate}
                tax_amount={current.tax_amount}
                total_amount={current.total_amount}
                amount_paid={current.amount_paid}
                balance_due={current.balance_due}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Bill to</CardTitle>
              <CardDescription>
                Copied from the client when the invoice was generated.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p className="font-medium">{current.client_name}</p>
              {current.client_contact_name ? (
                <p className="text-muted-foreground">
                  {current.client_contact_name}
                </p>
              ) : null}
              {current.client_address ? (
                <p className="whitespace-pre-line text-muted-foreground">
                  {current.client_address}
                </p>
              ) : null}
              {current.client_email ? (
                <p className="text-muted-foreground">{current.client_email}</p>
              ) : null}
              {current.client_tax_id ? (
                <p className="text-muted-foreground">
                  Tax ID: {current.client_tax_id}
                </p>
              ) : null}
              <Button asChild variant="link" size="sm" className="px-0">
                <Link to="/invoices/clients">Open client records</Link>
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Notes & terms</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              {current.terms ? (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide">
                    Payment terms
                  </p>
                  <p className="whitespace-pre-line">{current.terms}</p>
                </div>
              ) : null}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide">
                  Notes
                </p>
                <p className="whitespace-pre-line">
                  {current.notes || "No notes on this invoice."}
                </p>
              </div>
              {current.created_by_email ? (
                <p className="border-t pt-3 text-xs">
                  Generated by {current.created_by_email} on{" "}
                  {formatDateTime(current.created_at)}
                </p>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4" aria-hidden="true" />
                Invoice PDF
              </CardTitle>
              <CardDescription>
                Rendered on demand from the stored invoice snapshot.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => void handlePdf()}
                disabled={downloading === "pdf"}
              >
                <Download className="h-4 w-4" aria-hidden="true" />
                {downloading === "pdf" ? "Preparing…" : "Download PDF"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      <InvoiceFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        clients={clients.data?.results ?? []}
        invoice={current}
      />
      <SendInvoiceDialog
        open={sendOpen}
        onOpenChange={setSendOpen}
        invoice={current}
      />
      <RecordPaymentDialog
        open={paymentOpen}
        onOpenChange={setPaymentOpen}
        invoice={current}
      />
      <SendReminderDialog
        open={reminderOpen}
        onOpenChange={setReminderOpen}
        invoice={current}
      />
      <UploadInvoiceDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        invoice={current}
      />

      <Dialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        title={`Cancel ${current.invoice_number}?`}
        description="The invoice stays in the ledger with a cancelled status. This cannot be undone."
        footer={
          <>
            <Button
              type="button"
              variant="outline"
              onClick={() => setCancelOpen(false)}
              disabled={cancelMutation.isPending}
            >
              Keep invoice
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => void handleCancel()}
              disabled={cancelMutation.isPending}
            >
              {cancelMutation.isPending ? "Cancelling…" : "Cancel invoice"}
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted-foreground">
          Only draft or sent invoices with no recorded payment can be cancelled.
        </p>
      </Dialog>

      <Dialog
        open={removeTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRemoveTarget(null);
        }}
        title="Remove this file?"
        description={removeTarget?.original_name}
        footer={
          <>
            <Button
              type="button"
              variant="outline"
              onClick={() => setRemoveTarget(null)}
              disabled={deleteAttachment.isPending}
            >
              Keep file
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => void handleRemoveAttachment()}
              disabled={deleteAttachment.isPending}
            >
              {deleteAttachment.isPending ? "Removing…" : "Remove file"}
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted-foreground">
          The file is deleted from storage. The invoice itself is unchanged.
        </p>
      </Dialog>
    </div>
  );
}
