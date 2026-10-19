import type { ReactNode } from "react";

import type { AuditEntry } from "@/api/audit";
import { AuditActionBadge } from "@/components/audit/AuditActionBadge";
import { AuditChanges } from "@/components/audit/AuditChanges";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { formatDateTime } from "@/lib/format";

function Detail({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

export function AuditDetailDialog({
  entry,
  onClose,
}: {
  entry: AuditEntry | null;
  onClose: () => void;
}) {
  return (
    <Dialog
      open={entry !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={entry?.summary ?? "Audit event"}
      description={
        entry
          ? `${entry.action_label} · ${entry.model_label} #${entry.object_id}`
          : undefined
      }
      className="sm:max-w-2xl"
      footer={
        <Button type="button" onClick={onClose}>
          Close
        </Button>
      }
    >
      {entry ? (
        <div className="space-y-5">
          <dl className="grid gap-3 sm:grid-cols-2">
            <Detail label="Actor" value={entry.actor_label} />
            <Detail
              label="Action"
              value={
                <AuditActionBadge
                  action={entry.action}
                  label={entry.action_label}
                />
              }
            />
            <Detail
              label="Resource"
              value={`${entry.model_label} #${entry.object_id}`}
            />
            <Detail label="When" value={formatDateTime(entry.created_at)} />
          </dl>

          <div className="space-y-2">
            <h3 className="text-sm font-medium">Changes</h3>
            <AuditChanges changes={entry.changes} />
          </div>
        </div>
      ) : null}
    </Dialog>
  );
}
