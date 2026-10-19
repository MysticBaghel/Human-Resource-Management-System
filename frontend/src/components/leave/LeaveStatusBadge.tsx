import {
  LEAVE_STATUS_LABELS,
  type LeaveStatus,
} from "@/api/leave";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const STATUS_CLASSES: Record<LeaveStatus, string> = {
  pending: "border-amber-200 bg-amber-50 text-amber-800",
  approved: "border-emerald-200 bg-emerald-50 text-emerald-800",
  rejected: "border-red-200 bg-red-50 text-red-800",
  cancelled: "border-slate-200 bg-slate-100 text-slate-600",
};

export function LeaveStatusBadge({ status }: { status: LeaveStatus }) {
  return (
    <Badge variant="outline" className={cn("border", STATUS_CLASSES[status])}>
      {LEAVE_STATUS_LABELS[status]}
    </Badge>
  );
}
