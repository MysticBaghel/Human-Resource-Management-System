/** Adjust a draft payroll record before it is finalized. */

import { useEffect, useState } from "react";

import { ApiError } from "@/api/client";
import {
  useAdjustPayroll,
  type PayrollRecord,
} from "@/api/payroll";
import { FormError } from "@/components/form/FieldError";
import { SalaryBreakdown } from "@/components/payroll/SalaryBreakdown";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/form/Field";
import { toast } from "@/components/ui/toast";
import { formatMoney } from "@/lib/format";

type PayrollAdjustmentDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  record: PayrollRecord | null;
};

export function PayrollAdjustmentDialog({
  open,
  onOpenChange,
  record,
}: PayrollAdjustmentDialogProps) {
  const mutation = useAdjustPayroll();
  const [amount, setAmount] = useState("0");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !record) return;
    setAmount(String(record.adjustment_amount ?? 0));
    setNote(record.adjustment_note ?? "");
    setError(null);
  }, [open, record]);

  if (!record) return null;
  const payroll = record;

  const parsedAmount = Number(amount);
  const effectiveAmount = Number.isFinite(parsedAmount) ? parsedAmount : 0;
  const previewNet =
    payroll.gross_salary + effectiveAmount - payroll.total_deductions;

  async function handleSave() {
    if (!Number.isFinite(parsedAmount)) {
      setError("Enter a valid adjustment amount.");
      return;
    }
    if (previewNet < 0) {
      setError("The adjustment makes net salary negative.");
      return;
    }
    setError(null);
    try {
      await mutation.mutateAsync({
        id: payroll.id,
        adjustment_amount: effectiveAmount,
        adjustment_note: note.trim(),
      });
      toast({
        title: "Adjustment saved",
        description: `${payroll.employee_name} · net ${formatMoney(previewNet)}`,
        variant: "success",
      });
      onOpenChange(false);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Could not save the adjustment.",
      );
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Adjust ${payroll.employee_name}'s payroll`}
      description={`${payroll.pay_period} · ${payroll.payslip_number}`}
      className="sm:max-w-2xl"
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
            {mutation.isPending ? "Saving…" : "Save adjustment"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <FormError message={error ?? undefined} />

        <SalaryBreakdown
          values={{
            ...payroll,
            adjustment_amount: effectiveAmount,
            adjustment_note: note,
          }}
        />

        <Field
          id="adjustment-amount"
          label="Adjustment amount"
          hint="Positive adds to net pay; negative deducts. Use 0 to clear."
        >
          <Input
            id="adjustment-amount"
            type="number"
            inputMode="decimal"
            step="0.01"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
          />
        </Field>
        <Field id="adjustment-note" label="Reason" hint="Optional, shown on the record.">
          <Input
            id="adjustment-note"
            value={note}
            maxLength={255}
            placeholder="Bonus, correction, arrears…"
            onChange={(event) => setNote(event.target.value)}
          />
        </Field>
      </div>
    </Dialog>
  );
}
