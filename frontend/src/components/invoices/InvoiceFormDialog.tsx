/** Generate or edit an invoice with line items and a live total preview. */

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { ApiError } from "@/api/client";
import {
  useCreateInvoice,
  useUpdateInvoice,
  type Client,
  type InvoiceDetail,
  type InvoiceInput,
} from "@/api/invoices";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { InvoiceTotals } from "@/components/invoices/InvoiceTotals";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { toIsoDate } from "@/lib/date";
import { formatMoney } from "@/lib/format";

const itemSchema = z.object({
  description: z
    .string()
    .trim()
    .min(1, "Describe this line.")
    .max(255, "Keep the description under 255 characters."),
  quantity: z
    .number({ invalid_type_error: "Enter a quantity." })
    .positive("Quantity must be above zero."),
  unit_price: z
    .number({ invalid_type_error: "Enter a rate." })
    .min(0, "A rate cannot be negative."),
});

const baseSchema = z.object({
  client: z.string().min(1, "Choose a client."),
  issue_date: z.string().min(1, "Choose an issue date."),
  due_date: z.string().min(1, "Choose a due date."),
  reference: z.string().max(100, "Keep the reference under 100 characters."),
  notes: z.string().max(4000),
  terms: z.string().max(4000),
  discount_amount: z
    .number({ invalid_type_error: "Enter a discount." })
    .min(0, "A discount cannot be negative."),
  tax_rate: z
    .number({ invalid_type_error: "Enter a tax rate." })
    .min(0, "Tax cannot be negative.")
    .max(100, "Tax cannot exceed 100%."),
  items: z.array(itemSchema).min(1, "Add at least one line item."),
});

const schema = baseSchema.refine(
  (values) => values.due_date >= values.issue_date,
  {
    path: ["due_date"],
    message: "The due date must be on or after the issue date.",
  },
);

type FormValues = z.infer<typeof schema>;

function addDays(date: Date, days: number): string {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return toIsoDate(next);
}

function emptyItem(): FormValues["items"][number] {
  return { description: "", quantity: 1, unit_price: 0 };
}

function blankValues(): FormValues {
  const today = new Date();
  return {
    client: "",
    issue_date: toIsoDate(today),
    due_date: addDays(today, 30),
    reference: "",
    notes: "",
    terms: "Payment within 30 days by bank transfer.",
    discount_amount: 0,
    tax_rate: 0,
    items: [emptyItem()],
  };
}

function toFormValues(invoice: InvoiceDetail): FormValues {
  return {
    client: String(invoice.client),
    issue_date: invoice.issue_date,
    due_date: invoice.due_date,
    reference: invoice.reference,
    notes: invoice.notes,
    terms: invoice.terms,
    discount_amount: invoice.discount_amount,
    tax_rate: invoice.tax_rate,
    items: invoice.items.map((item) => ({
      description: item.description,
      quantity: item.quantity,
      unit_price: item.unit_price,
    })),
  };
}

type InvoiceFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  clients: Client[];
  invoice?: InvoiceDetail | null;
  onSaved?: (invoice: InvoiceDetail) => void;
};

export function InvoiceFormDialog({
  open,
  onOpenChange,
  clients,
  invoice,
  onSaved,
}: InvoiceFormDialogProps) {
  const createMutation = useCreateInvoice();
  const updateMutation = useUpdateInvoice(invoice?.id ?? 0);
  const isSaving = createMutation.isPending || updateMutation.isPending;
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    watch,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: blankValues(),
  });
  const { fields, append, remove } = useFieldArray({ control, name: "items" });

  useEffect(() => {
    if (!open) return;
    setFormError(null);
    reset(invoice ? toFormValues(invoice) : blankValues());
  }, [open, invoice, reset]);

  const values = watch();
  const subtotal = (values.items ?? []).reduce(
    (total, item) =>
      total + (Number(item.quantity) || 0) * (Number(item.unit_price) || 0),
    0,
  );
  const discount = Number(values.discount_amount) || 0;
  const taxable = Math.max(subtotal - discount, 0);
  const taxRate = Number(values.tax_rate) || 0;
  const taxAmount = (taxable * taxRate) / 100;
  const total = taxable + taxAmount;

  async function onSubmit(form: FormValues) {
    setFormError(null);
    const payload: InvoiceInput = {
      client: Number(form.client),
      issue_date: form.issue_date,
      due_date: form.due_date,
      reference: form.reference.trim(),
      notes: form.notes.trim(),
      terms: form.terms.trim(),
      discount_amount: Number(form.discount_amount).toFixed(2),
      tax_rate: Number(form.tax_rate).toFixed(2),
      items: form.items.map((item) => ({
        description: item.description.trim(),
        quantity: Number(item.quantity).toFixed(2),
        unit_price: Number(item.unit_price).toFixed(2),
      })),
    };

    try {
      const saved =
        invoice !== undefined && invoice !== null
          ? await updateMutation.mutateAsync(payload)
          : await createMutation.mutateAsync(payload);
      toast({
        title: invoice ? "Invoice updated" : "Invoice generated",
        description: `${saved.invoice_number} · ${formatMoney(saved.total_amount)}`,
        variant: "success",
      });
      onSaved?.(saved);
      onOpenChange(false);
    } catch (caught) {
      if (caught instanceof ApiError) {
        let handled = false;
        for (const [field, messages] of Object.entries(caught.fields)) {
          if (field in baseSchema.shape) {
            setError(field as keyof FormValues, { message: messages[0] });
            handled = true;
          }
        }
        if (!handled) setFormError(caught.message);
        return;
      }
      setFormError("Could not reach the server. Please try again.");
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={invoice ? `Edit ${invoice.invoice_number}` : "Generate invoice"}
      description={
        invoice
          ? "Drafts are editable. Once sent, the invoice is locked as a financial record."
          : "Line items, discount and tax are calculated on the server with exact decimals."
      }
      className="sm:max-w-4xl"
      footer={
        <>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSaving}
          >
            Cancel
          </Button>
          <Button type="submit" form="invoice-form" disabled={isSaving}>
            {isSaving
              ? "Saving…"
              : invoice
                ? "Save invoice"
                : "Generate invoice"}
          </Button>
        </>
      }
    >
      <form
        id="invoice-form"
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5"
        noValidate
      >
        <FormError message={formError ?? undefined} />

        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            id="invoice-client"
            label="Client"
            error={errors.client?.message}
            hint={
              clients.length === 0 ? (
                <span>
                  No active clients yet.{" "}
                  <Link to="/invoices/clients" className="underline">
                    Add a client first
                  </Link>
                  .
                </span>
              ) : undefined
            }
          >
            <Select
              id="invoice-client"
              aria-invalid={errors.client ? true : undefined}
              {...register("client")}
            >
              <option value="">Choose a client</option>
              {invoice && !clients.some((item) => item.id === invoice.client) ? (
                <option value={invoice.client}>{invoice.client_name}</option>
              ) : null}
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            id="invoice-reference"
            label="Reference / PO"
            error={errors.reference?.message}
            hint="Optional client reference or purchase order."
          >
            <Input id="invoice-reference" {...register("reference")} />
          </Field>
          <Field
            id="invoice-issue-date"
            label="Issue date"
            error={errors.issue_date?.message}
          >
            <Input
              id="invoice-issue-date"
              type="date"
              aria-invalid={errors.issue_date ? true : undefined}
              {...register("issue_date")}
            />
          </Field>
          <Field
            id="invoice-due-date"
            label="Due date"
            error={errors.due_date?.message}
          >
            <Input
              id="invoice-due-date"
              type="date"
              min={values.issue_date || undefined}
              aria-invalid={errors.due_date ? true : undefined}
              {...register("due_date")}
            />
          </Field>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Line items
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => append(emptyItem())}
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add line
            </Button>
          </div>

          {errors.items?.message ? (
            <p role="alert" className="text-sm font-medium text-destructive">
              {errors.items.message}
            </p>
          ) : null}

          <div className="space-y-3">
            {fields.map((field, index) => (
              <div
                key={field.id}
                className="grid gap-2 rounded-lg border bg-muted/10 p-3 sm:grid-cols-[1fr_90px_130px_auto]"
              >
                <Field
                  id={`item-description-${index}`}
                  label="Description"
                  error={errors.items?.[index]?.description?.message}
                >
                  <Input
                    id={`item-description-${index}`}
                    placeholder="Consulting services"
                    {...register(`items.${index}.description`)}
                  />
                </Field>
                <Field
                  id={`item-quantity-${index}`}
                  label="Qty"
                  error={errors.items?.[index]?.quantity?.message}
                >
                  <Input
                    id={`item-quantity-${index}`}
                    type="number"
                    inputMode="decimal"
                    min="0.01"
                    step="0.01"
                    {...register(`items.${index}.quantity`, {
                      valueAsNumber: true,
                    })}
                  />
                </Field>
                <Field
                  id={`item-price-${index}`}
                  label="Rate"
                  error={errors.items?.[index]?.unit_price?.message}
                >
                  <Input
                    id={`item-price-${index}`}
                    type="number"
                    inputMode="decimal"
                    min="0"
                    step="0.01"
                    {...register(`items.${index}.unit_price`, {
                      valueAsNumber: true,
                    })}
                  />
                </Field>
                <div className="flex items-end justify-between gap-2 sm:flex-col sm:items-end sm:justify-end">
                  <p className="text-sm font-medium tabular-nums">
                    {formatMoney(
                      (Number(values.items?.[index]?.quantity) || 0) *
                        (Number(values.items?.[index]?.unit_price) || 0),
                    )}
                  </p>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground"
                    onClick={() => remove(index)}
                    disabled={fields.length <= 1}
                    aria-label={`Remove line ${index + 1}`}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-4">
            <Field
              id="invoice-discount"
              label="Discount"
              error={errors.discount_amount?.message}
              hint="Applied before tax. Cannot exceed the subtotal."
            >
              <Input
                id="invoice-discount"
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                {...register("discount_amount", { valueAsNumber: true })}
              />
            </Field>
            <Field
              id="invoice-tax"
              label="Tax rate (%)"
              error={errors.tax_rate?.message}
            >
              <Input
                id="invoice-tax"
                type="number"
                inputMode="decimal"
                min="0"
                max="100"
                step="0.01"
                {...register("tax_rate", { valueAsNumber: true })}
              />
            </Field>
            <Field
              id="invoice-terms"
              label="Payment terms"
              error={errors.terms?.message}
              hint="Printed at the bottom of the invoice PDF."
            >
              <Textarea id="invoice-terms" rows={2} {...register("terms")} />
            </Field>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Live preview
            </p>
            <InvoiceTotals
              subtotal={subtotal}
              discount_amount={discount}
              tax_rate={taxRate}
              tax_amount={taxAmount}
              total_amount={total}
            />
          </div>
        </div>

        <Field
          id="invoice-notes"
          label="Notes"
          error={errors.notes?.message}
          hint="Optional note printed on the invoice."
        >
          <Textarea id="invoice-notes" rows={2} {...register("notes")} />
        </Field>
      </form>
    </Dialog>
  );
}
