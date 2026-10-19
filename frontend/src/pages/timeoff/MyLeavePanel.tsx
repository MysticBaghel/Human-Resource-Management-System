/** My time off for employees and managers: own balances and own requests only. */

import { CalendarPlus, Plus } from "lucide-react";
import { useState } from "react";

import { ApiError } from "@/api/client";
import {
  type LeaveRequest,
  useCancelLeaveRequest,
  useLeaveBalances,
  useLeaveRequests,
  useLeaveTypes,
} from "@/api/leave";
import { EmptyState, ErrorState } from "@/components/common/states";
import { BalanceCards } from "@/components/leave/BalanceCards";
import { LeaveStatusBadge } from "@/components/leave/LeaveStatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "@/components/ui/toast";
import { formatDateRange } from "@/lib/date";
import { formatDays } from "@/lib/format";
import { RequestLeaveDialog } from "./RequestLeaveDialog";

function RequestsSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-live="polite">
      {Array.from({ length: 4 }).map((_, index) => (
        <Skeleton key={index} className="h-12 w-full" />
      ))}
      <span className="sr-only">Loading your leave requests…</span>
    </div>
  );
}

export function MyLeavePanel() {
  const year = new Date().getFullYear();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [cancelTarget, setCancelTarget] = useState<LeaveRequest | null>(null);

  const {
    data: typesData,
    isLoading: typesLoading,
    isError: typesError,
    refetch: refetchTypes,
  } = useLeaveTypes();
  const {
    data: balancesData,
    isLoading: balancesLoading,
    isError: balancesError,
    error: balancesErrorValue,
    refetch: refetchBalances,
  } = useLeaveBalances(year);
  const {
    data: requestsData,
    isLoading: requestsLoading,
    isError: requestsError,
    error: requestsErrorValue,
    refetch: refetchRequests,
  } = useLeaveRequests({ mine: true, page_size: 100 });

  const cancelMutation = useCancelLeaveRequest();
  const leaveTypes = typesData?.results ?? [];
  const balances = balancesData?.results ?? [];
  const requests = requestsData?.results ?? [];
  const balancesPending = typesLoading || balancesLoading;

  function confirmCancel() {
    if (!cancelTarget) return;
    cancelMutation.mutate(cancelTarget.id, {
      onSuccess: () => {
        toast({
          title: "Leave cancelled",
          description: "Any deducted days have been returned.",
          variant: "success",
        });
        setCancelTarget(null);
      },
      onError: (caught) => {
        toast({
          title: "Could not cancel",
          description:
            caught instanceof ApiError ? caught.message : "Please try again.",
          variant: "destructive",
        });
      },
    });
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">My time off</h1>
          <p className="text-sm text-muted-foreground">
            Your balances and requests for {year}.
          </p>
        </div>
        <Button
          type="button"
          onClick={() => setDialogOpen(true)}
          disabled={leaveTypes.length === 0}
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Request leave
        </Button>
      </div>

      <section aria-labelledby="balances-heading" className="space-y-3">
        <h2 id="balances-heading" className="text-sm font-medium text-muted-foreground">
          Balances
        </h2>

        {balancesPending ? (
          <div className="grid gap-4 sm:grid-cols-3" aria-busy="true">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-32 w-full" />
            ))}
          </div>
        ) : typesError || balancesError ? (
          <ErrorState
            title="Could not load your balances"
            message={
              (balancesErrorValue as Error | null)?.message ??
              (typesError ? "Leave types could not be loaded." : undefined)
            }
            onRetry={() => {
              if (typesError) void refetchTypes();
              void refetchBalances();
            }}
          />
        ) : balances.length === 0 ? (
          <EmptyState
            title={`No leave allocated for ${year}`}
            description="Ask HR to run the yearly balance allocation."
          />
        ) : (
          <BalanceCards balances={balances} />
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">My requests</CardTitle>
          <CardDescription>
            Pending requests do not use balance until they are approved.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {requestsLoading ? (
            <RequestsSkeleton />
          ) : requestsError ? (
            <ErrorState
              title="Could not load your requests"
              message={(requestsErrorValue as Error | null)?.message}
              onRetry={() => void refetchRequests()}
            />
          ) : requests.length === 0 ? (
            <EmptyState
              title="No leave requests yet"
              description="Request leave and it will show up here while it waits for approval."
              action={
                <Button
                  type="button"
                  size="sm"
                  onClick={() => setDialogOpen(true)}
                  disabled={leaveTypes.length === 0}
                >
                  <CalendarPlus className="h-4 w-4" aria-hidden="true" />
                  Request leave
                </Button>
              }
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
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {requests.map((request) => (
                      <TableRow key={request.id}>
                        <TableCell>
                          <p className="font-medium">
                            {formatDateRange(request.start_date, request.end_date)}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {request.half_day ? "Half day" : ""}
                            {request.reviewer_name
                              ? `Reviewed by ${request.reviewer_name}`
                              : ""}
                          </p>
                        </TableCell>
                        <TableCell>{request.leave_type_name}</TableCell>
                        <TableCell>{formatDays(request.days)}</TableCell>
                        <TableCell>
                          <LeaveStatusBadge status={request.status} />
                        </TableCell>
                        <TableCell className="text-right">
                          {request.status === "pending" ||
                          request.status === "approved" ? (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => setCancelTarget(request)}
                            >
                              Cancel
                            </Button>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
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
                          day{request.days === 1 ? "" : "s"}
                        </p>
                      </div>
                      <LeaveStatusBadge status={request.status} />
                    </div>
                    {request.status === "pending" ||
                    request.status === "approved" ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="mt-2"
                        onClick={() => setCancelTarget(request)}
                      >
                        Cancel request
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardContent>
      </Card>

      {dialogOpen ? (
        <RequestLeaveDialog
          leaveTypes={leaveTypes}
          onClose={() => setDialogOpen(false)}
        />
      ) : null}

      <Dialog
        open={cancelTarget !== null}
        onOpenChange={(open) => {
          if (!open) setCancelTarget(null);
        }}
        title="Cancel this request?"
        description={
          cancelTarget
            ? `${cancelTarget.leave_type_name}, ${formatDateRange(
                cancelTarget.start_date,
                cancelTarget.end_date,
              )}.`
            : undefined
        }
        footer={
          <>
            <Button
              type="button"
              variant="outline"
              onClick={() => setCancelTarget(null)}
            >
              Keep it
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={confirmCancel}
              disabled={cancelMutation.isPending}
            >
              {cancelMutation.isPending ? "Cancelling…" : "Cancel request"}
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted-foreground">
          If it was already approved, the days go back to your balance
          immediately.
        </p>
      </Dialog>
    </div>
  );
}
