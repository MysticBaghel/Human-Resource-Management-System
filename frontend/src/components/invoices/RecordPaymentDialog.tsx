/** Record a full or partial payment against an invoice. */

import { useEffect, useState } from "react";

import { ApiError } from "@/api/client";
import {
  PAYMENT_METHOD_LABELS,
  useRecordInvoicePayment,
  type InvoiceDetail,
  type InvoicePaymentMethod,
} from "@/api/invoices";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { toIsoDate } from "@/lib/date";
import { formatMoney } from "@/lib/format";

const METHODS = Object.keys(PAYMENT_METHOD_LABELS) as InvoicePaymentMethod[];

type RecordPaymentDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  invoice: InvoiceDetail | null;
};

export function RecordPaymentDialog({
  open,
  onOpenChange,
  invoice,
}: RecordPaymentDialogProps) {
  const mutation = useRecordInvoicePayment();
  const [amount, setAmount] = useState("");
  const [paymentDate, setPaymentDate] = useState(toIsoDate(new Date()));
  const [method, setMethod] = useState<InvoicePaymentMethod>("bank_transfer");
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !invoice) return;
    setAmount(invoice.balance_due.toFixed(2));
    setPaymentDate(toIsoDate(new Date()));
    setMethod("bank_transfer");
    setReference("");
    setNote("");
    setError(null);
  }, [open, invoice]);

  if (!invoice) return null;
  const current = invoice;

  async function handleSave() {
    const parsed = Number(amount);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError("Enter a payment amount above zero.");
      return;
    }
    if (parsed > current.balance_due + 0.001) {
      setError("The payment cannot be greater than the balance due.");
      return;
    }
    if (!paymentDate) {
      setError("Choose the date the payment was received.");
      return;
    }

    setError(null);
    try {
      await mutation.mutateAsync({
        id: current.id,
        amount: parsed.toFixed(2),
        payment_date: paymentDate,
        method,
        reference: reference.trim(),
        note: note.trim(),
      });
      toast({
        title: "Payment recorded",
        description: `${current.invoice_number} · ${formatMoney(parsed)}`,
        variant: "success",
      });
      onOpenChange(false);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Could not record the payment.",
      );
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Record payment · ${current.invoice_number}`}
      description={`${current.client_name} · balance ${formatMoney(current.balance_due)}`}
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
          <Button type="button" onClick={handleSave} disabled={mutation.isPending}>
            {mutation.isPending ? "Saving…" : "Record payment"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <FormError message={error ?? undefined} />

        <div className="grid grid-cols-2 gap-3 rounded-lg border bg-muted/20 p-3 text-sm">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Invoice total
            </p>
            <p className="font-semibold tabular-nums">
              {formatMoney(current.total_amount)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Balance due
            </p>
            <p className="font-semibold tabular-nums text-primary">
              {formatMoney(current.balance_due)}
            </p>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="payment-amount" label="Amount received">
            <Input
              id="payment-amount"
              type="number"
              inputMode="decimal"
              min="0.01"
              step="0.01"
              max={current.balance_due}
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
            />
          </Field>
          <Field id="payment-date" label="Payment date">
            <Input
              id="payment-date"
              type="date"
              value={paymentDate}
              onChange={(event) => setPaymentDate(event.target.value)}
            />
          </Field>
          <Field id="payment-method" label="Method">
            <Select
              id="payment-method"
              value={method}
              onChange={(event) =>
                setMethod(event.target.value as InvoicePaymentMethod)
              }
            >
              {METHODS.map((value) => (
                <option key={value} value={value}>
                  {PAYMENT_METHOD_LABELS[value]}
                </option>
              ))}
            </Select>
          </Field>
          <Field id="payment-reference" label="Reference" hint="UTR, cheque no. or note.">
            <Input
              id="payment-reference"
              value={reference}
              maxLength={120}
              onChange={(event) => setReference(event.target.value)}
            />
          </Field>
        </div>

        <Field id="payment-note" label="Note" hint="Optional. Stored on the payment row.">
          <Textarea
            id="payment-note"
            rows={2}
            maxLength={255}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </Field>

        <p className="text-xs text-muted-foreground">
          This records the payment only; no gateway or bank transfer is contacted.
          A partial payment leaves the invoice open for the remainder.
        </p>
      </div>
    </Dialog>
  );
}
