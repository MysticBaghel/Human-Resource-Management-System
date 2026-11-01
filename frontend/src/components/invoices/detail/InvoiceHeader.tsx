import {
  ArrowLeft,
  Ban,
  Bell,
  Download,
  Pencil,
  Send,
  Upload,
  Wallet,
} from "lucide-react";
import { Link } from "react-router-dom";

import { InvoiceStatusBadge } from "@/components/invoices/InvoiceStatusBadge";
import { Button } from "@/components/ui/button";
import type { InvoiceDetail } from "@/api/invoices";
import { formatDate, formatDateTime } from "@/lib/format";

type InvoiceHeaderProps = {
  invoice: InvoiceDetail;
  downloadingPdf: boolean;
  onEdit: () => void;
  onSend: () => void;
  onRecordPayment: () => void;
  onSendReminder: () => void;
  onDownloadPdf: () => void;
  onUpload: () => void;
  onCancel: () => void;
};

export function InvoiceHeader({
  invoice,
  downloadingPdf,
  onEdit,
  onSend,
  onRecordPayment,
  onSendReminder,
  onDownloadPdf,
  onUpload,
  onCancel,
}: InvoiceHeaderProps) {
  return (
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
            {invoice.invoice_number}
          </h1>
          <InvoiceStatusBadge
            status={invoice.status}
            is_overdue={invoice.is_overdue}
          />
        </div>
        <p className="text-sm text-muted-foreground">
          {invoice.client_name} · issued {formatDate(invoice.issue_date)} ·
          due {formatDate(invoice.due_date)}
          {invoice.is_overdue
            ? ` · ${invoice.days_overdue} day${
                invoice.days_overdue === 1 ? "" : "s"
              } overdue`
            : ""}
        </p>
        {invoice.reference ? (
          <p className="text-xs text-muted-foreground">
            Reference: {invoice.reference}
          </p>
        ) : null}
        {invoice.sent_at ? (
          <p className="text-xs text-muted-foreground">
            Sent {formatDateTime(invoice.sent_at)}
            {invoice.sent_to ? ` to ${invoice.sent_to}` : ""}
            {invoice.sent_via === "gmail"
              ? " via Gmail"
              : invoice.sent_via === "django"
                ? " via email"
                : ""}
          </p>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        {invoice.is_editable ? (
          <Button
            type="button"
            variant="outline"
            onClick={() => onEdit()}
          >
            <Pencil className="h-4 w-4" aria-hidden="true" />
            Edit
          </Button>
        ) : null}
        {invoice.status === "draft" ? (
          <Button type="button" onClick={() => onSend()}>
            <Send className="h-4 w-4" aria-hidden="true" />
            Send invoice
          </Button>
        ) : null}
        {invoice.can_record_payment ? (
          <>
            <Button
              type="button"
              onClick={() => onRecordPayment()}
              variant="outline"
            >
              <Wallet className="h-4 w-4" aria-hidden="true" />
              Record payment
            </Button>
            <Button
              type="button"
              onClick={() => onSendReminder()}
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
          onClick={() => onDownloadPdf()}
          disabled={downloadingPdf}
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          {downloadingPdf ? "Preparing…" : "PDF"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => onUpload()}
        >
          <Upload className="h-4 w-4" aria-hidden="true" />
          Upload
        </Button>
        {invoice.can_cancel ? (
          <Button
            type="button"
            variant="ghost"
            className="text-destructive hover:text-destructive"
            onClick={() => onCancel()}
          >
            <Ban className="h-4 w-4" aria-hidden="true" />
            Cancel
          </Button>
        ) : null}
      </div>
    </div>
  </div>
  );
}
