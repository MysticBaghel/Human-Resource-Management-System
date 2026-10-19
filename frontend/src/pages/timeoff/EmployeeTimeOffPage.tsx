/** HR/admin view of one person's time off: the balance boxes and their requests. */

import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { useEmployee } from "@/api/employees";
import { useLeaveBalances, useLeaveRequests } from "@/api/leave";
import { EmptyState, ErrorState } from "@/components/common/states";
import { BalanceCards } from "@/components/leave/BalanceCards";
import { LeaveStatusBadge } from "@/components/leave/LeaveStatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDateRange } from "@/lib/date";
import { formatDays, initials } from "@/lib/format";

function requestedOn(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function PageSkeleton() {
  return (
    <div className="mx-auto w-full max-w-4xl space-y-6" aria-busy="true" aria-live="polite">
      <Skeleton className="h-4 w-28" />
      <div className="flex items-center gap-4">
        <Skeleton className="h-14 w-14 rounded-full" />
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <Skeleton key={index} className="h-32 w-full" />
        ))}
      </div>
      <Skeleton className="h-48 w-full" />
      <span className="sr-only">Loading this person's time off…</span>
    </div>
  );
}

export function EmployeeTimeOffPage() {
  const params = useParams();
  const parsedId = params.id ? Number(params.id) : Number.NaN;
  const employeeId = Number.isFinite(parsedId) ? parsedId : undefined;
  // A malformed URL must not turn into "all balances" for HR.
  const scopeId = employeeId ?? -1;
  const year = new Date().getFullYear();

  const {
    data: employee,
    isLoading: employeeLoading,
    isError,
    error,
    refetch,
  } = useEmployee(employeeId);
  const {
    data: balancesData,
    isLoading: balancesLoading,
    isError: balancesError,
    error: balancesErrorValue,
    refetch: refetchBalances,
  } = useLeaveBalances(year, scopeId);
  const {
    data: requestsData,
    isLoading: requestsLoading,
    isError: requestsError,
    error: requestsErrorValue,
    refetch: refetchRequests,
  } = useLeaveRequests({ employee: scopeId, page_size: 100 });

  const balances = balancesData?.results ?? [];
  const requests = requestsData?.results ?? [];

  if (employeeLoading) return <PageSkeleton />;

  if (isError || employee === undefined) {
    return (
      <div className="mx-auto w-full max-w-4xl space-y-6">
        <Link
          to="/time-off"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          All employees
        </Link>
        <ErrorState
          title="Could not load this person"
          message={
            error instanceof Error
              ? error.message
              : "They may not exist, or may be outside your scope."
          }
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <Link
        to="/time-off"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        All employees
      </Link>

      <div className="flex items-start gap-4">
        <div
          className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-secondary text-lg font-semibold"
          aria-hidden="true"
        >
          {initials(employee.full_name)}
        </div>
        <div className="min-w-0 space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            {employee.full_name}
          </h1>
          <p className="text-sm text-muted-foreground">
            {employee.job_title || "No job title"}
            {employee.team_name ? ` · ${employee.team_name}` : ""}
          </p>
        </div>
      </div>

      <section aria-labelledby="person-balances" className="space-y-3">
        <h2
          id="person-balances"
          className="text-sm font-medium text-muted-foreground"
        >
          Leave balances for {year}
        </h2>

        {balancesLoading ? (
          <div className="grid gap-4 sm:grid-cols-3" aria-busy="true">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-32 w-full" />
            ))}
          </div>
        ) : balancesError ? (
          <ErrorState
            title="Could not load the balances"
            message={(balancesErrorValue as Error | null)?.message}
            onRetry={() => void refetchBalances()}
          />
        ) : balances.length === 0 ? (
          <EmptyState
            title={`No balances for ${year}`}
            description="Balances for this year have not been allocated yet."
          />
        ) : (
          <BalanceCards balances={balances} />
        )}
      </section>

      <section aria-labelledby="person-requests" className="space-y-3">
        <h2
          id="person-requests"
          className="text-sm font-medium text-muted-foreground"
        >
          Leave requests
        </h2>

        {requestsLoading ? (
          <div className="space-y-2" aria-busy="true" aria-live="polite">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-12 w-full" />
            ))}
            <span className="sr-only">Loading requests…</span>
          </div>
        ) : requestsError ? (
          <ErrorState
            title="Could not load the requests"
            message={(requestsErrorValue as Error | null)?.message}
            onRetry={() => void refetchRequests()}
          />
        ) : requests.length === 0 ? (
          <EmptyState
            title="No leave requests"
            description="This person has not requested any leave yet."
          />
        ) : (
          <>
            <div className="hidden sm:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Dates</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Days</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Requested</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requests.map((request) => (
                    <TableRow key={request.id}>
                      <TableCell>
                        <p className="font-medium">
                          {formatDateRange(request.start_date, request.end_date)}
                        </p>
                        {request.half_day ? (
                          <p className="text-xs text-muted-foreground">Half day</p>
                        ) : null}
                      </TableCell>
                      <TableCell>{request.leave_type_name}</TableCell>
                      <TableCell>{formatDays(request.days)}</TableCell>
                      <TableCell>
                        <LeaveStatusBadge status={request.status} />
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {requestedOn(request.created_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <ul className="space-y-2 sm:hidden">
              {requests.map((request) => (
                <li key={request.id} className="rounded-lg border p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {formatDateRange(request.start_date, request.end_date)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {request.leave_type_name} · {formatDays(request.days)}{" "}
                        day{request.days === 1 ? "" : "s"} ·{" "}
                        {requestedOn(request.created_at)}
                      </p>
                    </div>
                    <LeaveStatusBadge status={request.status} />
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}
