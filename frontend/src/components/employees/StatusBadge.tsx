import type { EmployeeStatus } from "@/api/employees";
import { STATUS_LABELS } from "@/api/employees";
import { Badge } from "@/components/ui/badge";

export function StatusBadge({ status }: { status: EmployeeStatus }) {
  return (
    <Badge variant={status === "active" ? "success" : "secondary"}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
