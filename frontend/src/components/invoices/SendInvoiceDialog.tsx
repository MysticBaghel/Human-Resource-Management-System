/** Email a draft invoice with its PDF and mark it as sent. */

import { Mail, Paperclip } from "lucide-react";
import { useEffect, useState } from "react";

import { ApiError } from "@/api/client";
import { useSendInvoice, type InvoiceDetail } from "@/api/invoices";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { formatMoney } from "@/lib/format";

type SendInvoiceDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  invoice: InvoiceDetail | null;
};

export function SendInvoiceDialog({
  open,
  onOpenChange,
  invoice,
}: SendInvoiceDialogProps) {
  const mutation = useSendInvoice();
  const [recipient, setRecipient] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !invoice) return;
    setRecipient(invoice.client_email);
    setSubject("");
    setMessage("");
    setError(null);
  }, [open, invoice]);

  if (!invoice) return null;
  const current = invoice;

  async function handleSend() {
    if (!recipient.trim()) {
      setError("Enter the recipient email address.");
      return;
    }
    setError(null);
    try {
      const sent = await mutation.mutateAsync({
        id: current.id,
        recipient_email: recipient.trim(),
        subject: subject.trim(),
        message: message.trim(),
      });
      toast({
        title: "Invoice sent",
        description:
          sent.sent_via === "gmail"
            ? `${current.invoice_number} · sent with Gmail`
            : `${current.invoice_number} · sent to ${recipient.trim()}`,
        variant: "success",
      });
      onOpenChange(false);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Could not send the invoice.",
      );
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Send invoice ${current.invoice_number}`}
      description={`${current.client_name} · ${formatMoney(current.total_amount)}`}
      footer={
        <>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={mutation.isPending}
          >
            Cancel
          </Button>
          <Button type="button" onClick={handleSend} disabled={mutation.isPending}>
            <Mail className="h-4 w-4" aria-hidden="true" />
            {mutation.isPending ? "Sending…" : "Send invoice"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <FormError message={error ?? undefined} />

        <div className="flex items-start gap-3 rounded-lg border bg-muted/20 p-3">
          <Paperclip
            className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <div className="text-sm">
            <p className="font-medium">
              {current.invoice_number}.pdf is attached
            </p>
            <p className="text-xs text-muted-foreground">
              The invoice is marked sent only after the email is accepted.
            </p>
          </div>
        </div>

        <Field id="send-invoice-recipient" label="To">
          <Input
            id="send-invoice-recipient"
            type="email"
            value={recipient}
            onChange={(event) => setRecipient(event.target.value)}
            placeholder="billing@client.com"
          />
        </Field>
        <Field
          id="send-invoice-subject"
          label="Subject"
          hint="Leave blank to use the default invoice subject."
        >
          <Input
            id="send-invoice-subject"
            value={subject}
            maxLength={200}
            onChange={(event) => setSubject(event.target.value)}
          />
        </Field>
        <Field
          id="send-invoice-message"
          label="Message"
          hint="Leave blank to use the standard message, total and due date."
        >
          <Textarea
            id="send-invoice-message"
            rows={4}
            maxLength={5000}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Dear client, please find your invoice attached…"
          />
        </Field>

        <div className="rounded-md border border-amber-200 bg-amber-50/60 px-3 py-2 text-xs text-amber-900">
          Sending uses the Gmail API with OAuth 2.0 when it is configured. Without
          Gmail credentials, development prints the email in the backend console;
          production returns an error rather than silently marking the invoice
          sent.
        </div>
      </div>
    </Dialog>
  );
}
