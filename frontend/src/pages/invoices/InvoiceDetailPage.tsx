/** One invoice: line items, payments, reminders, uploads and PDF. */

import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import {
  downloadInvoiceAttachment,
  downloadInvoicePdf,
  useCancelInvoice,
  useClients,
  useDeleteInvoiceAttachment,
  useInvoice,
  type InvoiceAttachment,
} from "@/api/invoices";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/states";
import { InvoiceAttachmentsCard } from "@/components/invoices/detail/InvoiceAttachmentsCard";
import { InvoiceHeader } from "@/components/invoices/detail/InvoiceHeader";
import { InvoiceLineItemsCard } from "@/components/invoices/detail/InvoiceLineItemsCard";
import { InvoiceMetrics } from "@/components/invoices/detail/InvoiceMetrics";
import { InvoicePaymentsCard } from "@/components/invoices/detail/InvoicePaymentsCard";
import { InvoiceRemindersCard } from "@/components/invoices/detail/InvoiceRemindersCard";
import { InvoiceSummarySidebar } from "@/components/invoices/detail/InvoiceSummarySidebar";
import { InvoiceFormDialog } from "@/components/invoices/InvoiceFormDialog";
import { RecordPaymentDialog } from "@/components/invoices/RecordPaymentDialog";
import { SendInvoiceDialog } from "@/components/invoices/SendInvoiceDialog";
import { SendReminderDialog } from "@/components/invoices/SendReminderDialog";
import { UploadInvoiceDialog } from "@/components/invoices/UploadInvoiceDialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { errorMessage, showError } from "@/lib/errors";

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
          message={errorMessage(error)}
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const current = invoice;

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
      showError("Could not cancel the invoice", caught);
    }
  }

  async function handlePdf() {
    setDownloading("pdf");
    try {
      await downloadInvoicePdf(current);
    } catch (caught) {
      showError("Could not download the invoice", caught);
    } finally {
      setDownloading(null);
    }
  }

  async function handleAttachment(attachment: InvoiceAttachment) {
    setDownloading(`attachment-${attachment.id}`);
    try {
      await downloadInvoiceAttachment(current.id, attachment);
    } catch (caught) {
      showError("Could not download the file", caught);
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
      showError("Could not remove the file", caught);
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <InvoiceHeader
        invoice={current}
        downloadingPdf={downloading === "pdf"}
        onEdit={() => setEditOpen(true)}
        onSend={() => setSendOpen(true)}
        onRecordPayment={() => setPaymentOpen(true)}
        onSendReminder={() => setReminderOpen(true)}
        onDownloadPdf={() => void handlePdf()}
        onUpload={() => setUploadOpen(true)}
        onCancel={() => setCancelOpen(true)}
      />

      <InvoiceMetrics invoice={current} />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <InvoiceLineItemsCard items={current.items} />
          <InvoicePaymentsCard
            payments={current.payments}
            canRecord={current.can_record_payment}
            onRecord={() => setPaymentOpen(true)}
          />
          <InvoiceRemindersCard
            reminders={current.reminders}
            canRemind={current.can_record_payment}
            onSend={() => setReminderOpen(true)}
          />
          <InvoiceAttachmentsCard
            attachments={current.attachments}
            downloading={downloading}
            onUpload={() => setUploadOpen(true)}
            onDownload={(attachment) => void handleAttachment(attachment)}
            onRemove={setRemoveTarget}
          />
        </div>

        <InvoiceSummarySidebar
          invoice={current}
          downloadingPdf={downloading === "pdf"}
          onDownloadPdf={() => void handlePdf()}
        />
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

      <ConfirmDialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        title={`Cancel ${current.invoice_number}?`}
        description="The invoice stays in the ledger with a cancelled status. This cannot be undone."
        cancelLabel="Keep invoice"
        confirmLabel="Cancel invoice"
        pendingLabel="Cancelling…"
        isPending={cancelMutation.isPending}
        onConfirm={() => void handleCancel()}
      >
        Only draft or sent invoices with no recorded payment can be cancelled.
      </ConfirmDialog>

      <ConfirmDialog
        open={removeTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRemoveTarget(null);
        }}
        title="Remove this file?"
        description={removeTarget?.original_name}
        cancelLabel="Keep file"
        confirmLabel="Remove file"
        pendingLabel="Removing…"
        isPending={deleteAttachment.isPending}
        onConfirm={() => void handleRemoveAttachment()}
      >
        The file is deleted from storage. The invoice itself is unchanged.
      </ConfirmDialog>
    </div>
  );
}
