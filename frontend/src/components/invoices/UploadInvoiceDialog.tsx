/** Upload a PDF or image against an invoice (original, signed copy, receipt). */

import { Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ApiError } from "@/api/client";
import {
  ATTACHMENT_KIND_LABELS,
  useUploadInvoiceAttachment,
  type InvoiceAttachmentKind,
  type InvoiceDetail,
} from "@/api/invoices";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { toast } from "@/components/ui/toast";

const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".webp"];
const KINDS = Object.keys(ATTACHMENT_KIND_LABELS) as InvoiceAttachmentKind[];

type UploadInvoiceDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  invoice: InvoiceDetail | null;
};

function validateFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ALLOWED_EXTENSIONS.some((extension) => name.endsWith(extension))) {
    return "Choose a PDF, PNG, JPG or WEBP file.";
  }
  if (file.size > MAX_BYTES) {
    return "The file must be 10 MB or smaller.";
  }
  return null;
}

export function UploadInvoiceDialog({
  open,
  onOpenChange,
  invoice,
}: UploadInvoiceDialogProps) {
  const mutation = useUploadInvoiceAttachment(invoice?.id ?? 0);
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState<InvoiceAttachmentKind>("original");
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setFile(null);
    setKind("original");
    setTitle("");
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }, [open]);

  if (!invoice) return null;
  const current = invoice;

  function chooseFile(next: File | null) {
    setError(null);
    if (!next) {
      setFile(null);
      return;
    }
    const problem = validateFile(next);
    if (problem) {
      setError(problem);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setFile(next);
    if (!title) setTitle(next.name.replace(/\.[^.]+$/, ""));
  }

  async function handleUpload() {
    if (!file) {
      setError("Choose a file to upload.");
      return;
    }
    setError(null);
    try {
      await mutation.mutateAsync({ file, kind, title: title.trim() });
      toast({
        title: "File uploaded",
        description: `${file.name} · ${current.invoice_number}`,
        variant: "success",
      });
      onOpenChange(false);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Could not upload the file.",
      );
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Upload invoice file · ${current.invoice_number}`}
      description="Keep the original document, a signed copy or a payment receipt with the invoice."
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
          <Button type="button" onClick={handleUpload} disabled={mutation.isPending}>
            {mutation.isPending ? "Uploading…" : "Upload file"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <FormError message={error ?? undefined} />

        <Field
          id="invoice-file"
          label="File"
          hint="PDF, PNG, JPG or WEBP, up to 10 MB."
        >
          <Input
            ref={inputRef}
            id="invoice-file"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/png,image/jpeg,image/webp"
            onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
          />
        </Field>

        {file ? (
          <p className="flex items-center gap-2 rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            <Upload className="h-3.5 w-3.5" aria-hidden="true" />
            {file.name} · {(file.size / 1024).toFixed(0)} KB
          </p>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="invoice-file-kind" label="What is this?">
            <Select
              id="invoice-file-kind"
              value={kind}
              onChange={(event) =>
                setKind(event.target.value as InvoiceAttachmentKind)
              }
            >
              {KINDS.map((value) => (
                <option key={value} value={value}>
                  {ATTACHMENT_KIND_LABELS[value]}
                </option>
              ))}
            </Select>
          </Field>
          <Field id="invoice-file-title" label="Title" hint="Optional label.">
            <Input
              id="invoice-file-title"
              value={title}
              maxLength={200}
              onChange={(event) => setTitle(event.target.value)}
            />
          </Field>
        </div>
      </div>
    </Dialog>
  );
}
