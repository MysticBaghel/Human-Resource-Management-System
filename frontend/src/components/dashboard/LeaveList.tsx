import type { LeaveRequest } from "@/api/leave";
import { LeaveStatusBadge } from "@/components/leave/LeaveStatusBadge";
import { formatDateRange } from "@/lib/date";
import { formatDays } from "@/lib/format";

export function LeaveList({
  requests,
  empty,
  showEmployee = true,
  showStatus = true,
}: {
  requests: LeaveRequest[];
  empty: string;
  showEmployee?: boolean;
  showStatus?: boolean;
}) {
  if (requests.length === 0) {
    return <p className="text-sm text-muted-foreground">{empty}</p>;
  }

  return (
    <ul className="divide-y">
      {requests.map((request) => (
        <li
          key={request.id}
          className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0"
        >
          <div className="min-w-0 space-y-1">
            {showEmployee ? (
              <p className="text-sm font-medium">{request.employee_name}</p>
            ) : null}
            <p
              className={
                showEmployee
                  ? "text-xs text-muted-foreground"
                  : "text-sm font-medium"
              }
            >
              {request.leave_type_name} ·{" "}
              {formatDateRange(request.start_date, request.end_date)} ·{" "}
              {formatDays(request.days)} day{request.days === 1 ? "" : "s"}
            </p>
            {request.reviewer_name && request.status !== "pending" ? (
              <p className="text-xs text-muted-foreground">
                by {request.reviewer_name}
              </p>
            ) : null}
          </div>
          {showStatus ? <LeaveStatusBadge status={request.status} /> : null}
        </li>
      ))}
    </ul>
  );
}
