import type { AuditAction } from "@/api/audit";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const CLASSES: Record<AuditAction, string> = {
  create: "border-emerald-200 bg-emerald-50 text-emerald-800",
  update: "border-sky-200 bg-sky-50 text-sky-800",
  delete: "border-red-200 bg-red-50 text-red-800",
};

export function AuditActionBadge({
  action,
  label,
}: {
  action: AuditAction;
  label: string;
}) {
  return (
    <Badge variant="outline" className={cn("border", CLASSES[action])}>
      {label}
    </Badge>
  );
}
