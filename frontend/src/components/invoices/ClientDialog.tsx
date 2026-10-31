/** Create or edit a billing client. */

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ApiError } from "@/api/client";
import {
  useCreateClient,
  useUpdateClient,
  type Client,
  type ClientInput,
} from "@/api/invoices";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";

const schema = z.object({
  name: z.string().trim().min(1, "A client name is required.").max(200),
  contact_name: z.string().max(160),
  email: z
    .string()
    .trim()
    .email("Enter a valid email address.")
    .or(z.literal("")),
  phone: z.string().max(40),
  billing_address: z.string().max(2000),
  tax_id: z.string().max(40),
  notes: z.string().max(2000),
  is_active: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

function blankValues(): FormValues {
  return {
    name: "",
    contact_name: "",
    email: "",
    phone: "",
    billing_address: "",
    tax_id: "",
    notes: "",
    is_active: true,
  };
}

function toFormValues(client: Client): FormValues {
  return {
    name: client.name,
    contact_name: client.contact_name,
    email: client.email,
    phone: client.phone,
    billing_address: client.billing_address,
    tax_id: client.tax_id,
    notes: client.notes,
    is_active: client.is_active,
  };
}

type ClientDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  client?: Client | null;
};

export function ClientDialog({ open, onOpenChange, client }: ClientDialogProps) {
  const createMutation = useCreateClient();
  const updateMutation = useUpdateClient(client?.id ?? 0);
  const isSaving = createMutation.isPending || updateMutation.isPending;
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: blankValues(),
  });

  useEffect(() => {
    if (!open) return;
    setFormError(null);
    reset(client ? toFormValues(client) : blankValues());
  }, [open, client, reset]);

  async function onSubmit(values: FormValues) {
    setFormError(null);
    const payload: ClientInput = {
      name: values.name.trim(),
      contact_name: values.contact_name.trim(),
      email: values.email.trim(),
      phone: values.phone.trim(),
      billing_address: values.billing_address.trim(),
      tax_id: values.tax_id.trim(),
      notes: values.notes.trim(),
      is_active: values.is_active,
    };

    try {
      if (client) {
        await updateMutation.mutateAsync(payload);
      } else {
        await createMutation.mutateAsync(payload);
      }
      toast({
        title: client ? "Client updated" : "Client added",
        description: payload.name,
        variant: "success",
      });
      onOpenChange(false);
    } catch (caught) {
      if (caught instanceof ApiError) {
        let handled = false;
        for (const [field, messages] of Object.entries(caught.fields)) {
          if (field in schema.shape) {
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
      title={client ? "Edit client" : "New client"}
      description="Billing details are copied onto each invoice when it is generated."
      className="sm:max-w-2xl"
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
          <Button type="submit" form="client-form" disabled={isSaving}>
            {isSaving ? "Saving…" : client ? "Save client" : "Add client"}
          </Button>
        </>
      }
    >
      <form
        id="client-form"
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
        noValidate
      >
        <FormError message={formError ?? undefined} />

        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="client-name" label="Client name" error={errors.name?.message}>
            <Input id="client-name" placeholder="Acme Industries" {...register("name")} />
          </Field>
          <Field
            id="client-contact"
            label="Contact person"
            error={errors.contact_name?.message}
          >
            <Input id="client-contact" {...register("contact_name")} />
          </Field>
          <Field id="client-email" label="Billing email" error={errors.email?.message}>
            <Input
              id="client-email"
              type="email"
              placeholder="billing@acme.com"
              {...register("email")}
            />
          </Field>
          <Field id="client-phone" label="Phone" error={errors.phone?.message}>
            <Input id="client-phone" {...register("phone")} />
          </Field>
          <Field
            id="client-tax"
            label="Tax ID / GSTIN"
            error={errors.tax_id?.message}
            hint="Printed on the invoice when set."
          >
            <Input id="client-tax" {...register("tax_id")} />
          </Field>
          <div className="flex items-center gap-2 pt-1 sm:pt-7">
            <input
              id="client-active"
              type="checkbox"
              className="h-4 w-4 rounded border-input"
              {...register("is_active")}
            />
            <label htmlFor="client-active" className="text-sm">
              Active client
            </label>
          </div>
        </div>

        <Field
          id="client-address"
          label="Billing address"
          error={errors.billing_address?.message}
        >
          <Textarea id="client-address" rows={3} {...register("billing_address")} />
        </Field>

        <Field
          id="client-notes"
          label="Internal notes"
          error={errors.notes?.message}
          hint="Not printed on the invoice."
        >
          <Textarea id="client-notes" rows={2} {...register("notes")} />
        </Field>
      </form>
    </Dialog>
  );
}
