import type { AuditEntry } from "@/api/audit";
import { AuditActionBadge } from "@/components/audit/AuditActionBadge";
import { formatDateTime } from "@/lib/format";

export function ActivityList({
  entries,
  empty = "No activity yet.",
}: {
  entries: AuditEntry[];
  empty?: string;
}) {
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">{empty}</p>;
  }

  return (
    <ul className="divide-y">
      {entries.map((entry) => (
        <li
          key={entry.id}
          className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0"
        >
          <div className="min-w-0 space-y-1">
            <p className="text-sm font-medium">{entry.summary}</p>
            <p className="text-xs text-muted-foreground">
              {entry.actor_label} · {formatDateTime(entry.created_at)}
            </p>
          </div>
          <AuditActionBadge
            action={entry.action}
            label={entry.action_label}
          />
        </li>
      ))}
    </ul>
  );
}
