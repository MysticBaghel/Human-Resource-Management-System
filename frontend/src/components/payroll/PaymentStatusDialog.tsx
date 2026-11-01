/** Record a payment outcome for a finalized payroll record. */

import { useEffect, useState } from "react";

import { ApiError } from "@/api/client";
import {
  PAYMENT_STATUS_LABELS,
  useUpdatePayment,
  type PaymentStatus,
  type PayrollRecord,
} from "@/api/payroll";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { formatMoney } from "@/lib/format";

// Cancelled deliberately sits below Failed.
const STATUSES: PaymentStatus[] = ["pending", "paid", "failed", "cancelled"];

type PaymentStatusDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  record: PayrollRecord | null;
};

export function PaymentStatusDialog({
  open,
  onOpenChange,
  record,
}: PaymentStatusDialogProps) {
  const mutation = useUpdatePayment();
  const [status, setStatus] = useState<PaymentStatus>("pending");
  const [paymentDate, setPaymentDate] = useState("");
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !record) return;
    setStatus(record.payment_status);
    setPaymentDate(record.payment_date ?? "");
    setReference(record.payment_reference ?? "");
    setError(null);
  }, [open, record]);

  if (!record) return null;
  const payroll = record;

  async function handleSave() {
    if (status === "paid" && !paymentDate) {
      setError("Choose the date the payment was made.");
      return;
    }
    setError(null);
    try {
      await mutation.mutateAsync({
        id: payroll.id,
        payment_status: status,
        payment_date: paymentDate || null,
        payment_reference: reference.trim(),
      });
      toast({
        title: "Payment status updated",
        description: `${payroll.employee_name} · ${PAYMENT_STATUS_LABELS[status]}`,
        variant:
          status === "failed" || status === "cancelled"
            ? "destructive"
            : "success",
      });
      onOpenChange(false);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Could not update the payment.",
      );
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Payment · ${payroll.employee_name}`}
      description={`${payroll.pay_period} · net ${formatMoney(payroll.net_salary)}`}
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
            {mutation.isPending ? "Saving…" : "Save payment"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <FormError message={error ?? undefined} />
        <Field id="payment-status" label="Payment status">
          <Select
            id="payment-status"
            value={status}
            onChange={(event) => {
              const next = event.target.value as PaymentStatus;
              setStatus(next);
              // Match the API: pending and cancelled do not keep a date.
              if (next === "pending" || next === "cancelled") {
                setPaymentDate("");
              }
            }}
          >
            {STATUSES.map((value) => (
              <option key={value} value={value}>
                {PAYMENT_STATUS_LABELS[value]}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          id="payment-date"
          label="Payment date"
          hint="Required when the status is Paid."
        >
          <Input
            id="payment-date"
            type="date"
            value={paymentDate}
            onChange={(event) => setPaymentDate(event.target.value)}
          />
        </Field>
        <Field
          id="payment-reference"
          label="Payment reference"
          hint="Bank reference, UTR or internal note. Optional."
        >
          <Input
            id="payment-reference"
            value={reference}
            maxLength={120}
            onChange={(event) => setReference(event.target.value)}
          />
        </Field>
        {status !== "paid" && paymentDate ? (
          <Button
            type="button"
            variant="link"
            size="sm"
            className="px-0"
            onClick={() => setPaymentDate("")}
          >
            Clear the payment date
          </Button>
        ) : null}
        {status === "cancelled" ? (
          <p className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs text-muted-foreground">
            The finalized payroll stays in the list for audit, its payment date
            is cleared, and the payslip snapshot is unchanged.
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">
            This records the outcome only; no bank transfer or payment gateway is
            contacted.
          </p>
        )}
      </div>
    </Dialog>
  );
}
