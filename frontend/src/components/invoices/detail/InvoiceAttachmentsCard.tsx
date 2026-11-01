import { Download, Paperclip, Trash2, Upload } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import type { InvoiceAttachment, InvoiceDetail } from "@/api/invoices";
import { formatDateTime } from "@/lib/format";

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(0)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

type InvoiceAttachmentsCardProps = {
  attachments: InvoiceDetail["attachments"];
  /** Key of the download in flight, e.g. `attachment-3`. */
  downloading: string | null;
  onUpload: () => void;
  onDownload: (attachment: InvoiceAttachment) => void;
  onRemove: (attachment: InvoiceAttachment) => void;
};

export function InvoiceAttachmentsCard({
  attachments,
  downloading,
  onUpload,
  onDownload,
  onRemove,
}: InvoiceAttachmentsCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
        <div className="space-y-1">
          <CardTitle className="text-base">Uploaded files</CardTitle>
          <CardDescription>
            Scanned invoice, signed copy, receipt or supporting document.
          </CardDescription>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onUpload()}
        >
          <Upload className="h-4 w-4" aria-hidden="true" />
          Upload
        </Button>
      </CardHeader>
      <CardContent>
        {attachments.length === 0 ? (
          <EmptyState
            title="No files uploaded"
            description="Upload the original invoice or a signed copy as a PDF or image."
            action={
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onUpload()}
              >
                Upload a file
              </Button>
            }
          />
        ) : (
          <ul className="space-y-2">
            {attachments.map((attachment) => (
              <li
                key={attachment.id}
                className="flex flex-col gap-2 rounded-lg border p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex min-w-0 items-start gap-2">
                  <Paperclip
                    className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {attachment.title || attachment.original_name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {attachment.kind_label} ·{" "}
                      {formatBytes(attachment.size)} ·{" "}
                      {formatDateTime(attachment.created_at)}
                      {attachment.uploaded_by_email
                        ? ` · ${attachment.uploaded_by_email}`
                        : ""}
                    </p>
                  </div>
                </div>
                <div className="flex gap-1 sm:shrink-0">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => onDownload(attachment)}
                    disabled={downloading === `attachment-${attachment.id}`}
                  >
                    <Download className="h-4 w-4" aria-hidden="true" />
                    {downloading === `attachment-${attachment.id}`
                      ? "…"
                      : "Download"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-9 w-9 text-muted-foreground"
                    onClick={() => onRemove(attachment)}
                    aria-label={`Remove ${attachment.original_name}`}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
