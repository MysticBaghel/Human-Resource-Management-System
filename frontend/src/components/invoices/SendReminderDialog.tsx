/** Email a payment reminder for an outstanding invoice. */

import { useEffect, useState } from "react";

import { ApiError } from "@/api/client";
import { useSendInvoiceReminder, type InvoiceDetail } from "@/api/invoices";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { formatDate, formatMoney } from "@/lib/format";

type SendReminderDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  invoice: InvoiceDetail | null;
};

export function SendReminderDialog({
  open,
  onOpenChange,
  invoice,
}: SendReminderDialogProps) {
  const mutation = useSendInvoiceReminder();
  const [recipient, setRecipient] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !invoice) return;
    setRecipient(invoice.client_email);
    setSubject(`Payment reminder: ${invoice.invoice_number}`);
    setMessage("");
    setError(null);
  }, [open, invoice]);

  if (!invoice) return null;
  const current = invoice;

  async function handleSend() {
    if (!recipient.trim()) {
      setError("Enter a recipient email address.");
      return;
    }
    setError(null);
    try {
      await mutation.mutateAsync({
        id: current.id,
        recipient_email: recipient.trim(),
        subject: subject.trim(),
        message: message.trim(),
      });
      toast({
        title: "Reminder sent",
        description: `${current.invoice_number} · ${recipient.trim()}`,
        variant: "success",
      });
      onOpenChange(false);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Could not send the reminder.",
      );
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Send reminder · ${current.invoice_number}`}
      description={`${current.client_name} · due ${formatDate(
        current.due_date,
      )} · ${formatMoney(current.balance_due)} outstanding`}
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
          <Button
            type="button"
            onClick={handleSend}
            disabled={mutation.isPending || !current.reminder_due}
          >
            {mutation.isPending ? "Sending…" : "Send reminder"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <FormError message={error ?? undefined} />

        {!current.reminder_due ? (
          <div
            role="status"
            className="rounded-md border bg-muted/40 px-3 py-2 text-sm text-muted-foreground"
          >
            A reminder was sent recently. The cooldown stops the same invoice
            being nudged repeatedly; try again after the cooldown window.
          </div>
        ) : null}

        <Field id="reminder-recipient" label="Recipient">
          <Input
            id="reminder-recipient"
            type="email"
            value={recipient}
            onChange={(event) => setRecipient(event.target.value)}
            placeholder="billing@client.com"
          />
        </Field>
        <Field id="reminder-subject" label="Subject">
          <Input
            id="reminder-subject"
            value={subject}
            maxLength={200}
            onChange={(event) => setSubject(event.target.value)}
          />
        </Field>
        <Field
          id="reminder-message"
          label="Message"
          hint="Leave blank to use the standard reminder with the amount, due date and payment terms."
        >
          <Textarea
            id="reminder-message"
            rows={5}
            maxLength={5000}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Dear client, this is a reminder that…"
          />
        </Field>

        <p className="text-xs text-muted-foreground">
          The email is sent through Django's configured email backend. In
          development it is printed to the runserver console.
        </p>
      </div>
    </Dialog>
  );
}
