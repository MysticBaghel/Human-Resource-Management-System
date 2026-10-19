/** Leave decisions: the full ledger for HR/admin, the pending queue for managers. */

import { Check, X } from "lucide-react";
import { useState } from "react";

import { ApiError } from "@/api/client";
import {
  type LeaveRequest,
  type LeaveRequestFilters,
  useLeaveRequests,
  useReviewLeaveRequest,
} from "@/api/leave";
import { useAuth } from "@/auth/AuthContext";
import { EmptyState, ErrorState } from "@/components/common/states";
import { LeaveStatusBadge } from "@/components/leave/LeaveStatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { formatDateRange } from "@/lib/date";
import { formatDays } from "@/lib/format";

function requestedOn(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function ListSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-live="polite">
      {Array.from({ length: 3 }).map((_, index) => (
        <Skeleton key={index} className="h-24 w-full" />
      ))}
      <span className="sr-only">Loading leave requests…</span>
    </div>
  );
}

export function ApprovalsPage() {
  const { hasRole } = useAuth();
  // HR and admin get the complete history; managers get the queue they act on.
  const seesLedger = hasRole("admin", "hr");
  const filters: LeaveRequestFilters = seesLedger
    ? { page_size: 100 }
    : { status: "pending", page_size: 100 };

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useLeaveRequests(filters);
  const reviewMutation = useReviewLeaveRequest();
  const [comments, setComments] = useState<Record<number, string>>({});
  const requests = data?.results ?? [];

  function decide(request: LeaveRequest, action: "approve" | "reject") {
    const comment = (comments[request.id] ?? "").trim();
    if (action === "reject" && comment.length === 0) {
      toast({
        title: "A comment is required to reject",
        description: "Say why, so the person knows what to do next.",
        variant: "destructive",
      });
      return;
    }

    reviewMutation.mutate(
      { id: request.id, action, comment },
      {
        onSuccess: () => {
          toast({
            title: action === "approve" ? "Leave approved" : "Leave rejected",
            description: `${request.employee_name} · ${formatDateRange(
              request.start_date,
              request.end_date,
            )}`,
            variant: "success",
          });
          setComments((current) => {
            const next = { ...current };
            delete next[request.id];
            return next;
          });
        },
        onError: (caught) => {
          toast({
            title: "Could not save the decision",
            description:
              caught instanceof ApiError ? caught.message : "Please try again.",
            variant: "destructive",
          });
        },
      },
    );
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          {seesLedger ? "Leave status" : "Approvals"}
        </h1>
        <p className="text-sm text-muted-foreground">
          {seesLedger
            ? "Every leave request in the company, newest first. Pending requests can be decided here."
            : "Pending leave from your team. Approving deducts the balance; rejecting leaves it untouched."}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {seesLedger ? "All leave requests" : "Waiting for you"}
          </CardTitle>
          <CardDescription>
            {data
              ? `${data.count} request${data.count === 1 ? "" : "s"} · newest first`
              : "Loading leave requests"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <ErrorState
              title="Could not load leave requests"
              message={error instanceof Error ? error.message : undefined}
              onRetry={() => void refetch()}
            />
          ) : requests.length === 0 ? (
            <EmptyState
              title={
                seesLedger
                  ? "No leave requests yet"
                  : "Nothing waiting for approval"
              }
              description={
                seesLedger
                  ? "Requests from everyone in the company will appear here."
                  : "When someone requests leave, it shows up here."
              }
            />
          ) : (
            <>
              <div className="hidden lg:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead>Leave</TableHead>
                      <TableHead>Requested</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Comment</TableHead>
                      <TableHead className="text-right">Decision</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {requests.map((request) => (
                      <TableRow key={request.id} className="align-top">
                        <TableCell>
                          <p className="font-medium">{request.employee_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {request.half_day ? "Half day" : "Full day"}
                          </p>
                        </TableCell>
                        <TableCell>
                          <p>{request.leave_type_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatDateRange(
                              request.start_date,
                              request.end_date,
                            )}{" "}
                            · {formatDays(request.days)} day
                            {request.days === 1 ? "" : "s"}
                          </p>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {requestedOn(request.created_at)}
                        </TableCell>
                        <TableCell>
                          <LeaveStatusBadge status={request.status} />
                          {request.reviewer_name ? (
                            <p className="mt-1 text-xs text-muted-foreground">
                              {request.reviewer_name}
                            </p>
                          ) : null}
                        </TableCell>
                        <TableCell className="min-w-[220px]">
                          {request.status === "pending" ? (
                            <>
                              <label
                                htmlFor={`comment-${request.id}`}
                                className="sr-only"
                              >
                                Comment for {request.employee_name}
                              </label>
                              <Textarea
                                id={`comment-${request.id}`}
                                value={comments[request.id] ?? ""}
                                onChange={(event) =>
                                  setComments((current) => ({
                                    ...current,
                                    [request.id]: event.target.value,
                                  }))
                                }
                                placeholder="Required to reject, optional to approve"
                                className="min-h-[60px] text-sm"
                              />
                            </>
                          ) : (
                            <p className="text-sm text-muted-foreground">
                              {request.review_comment || "—"}
                            </p>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {request.status === "pending" ? (
                            <div className="flex justify-end gap-2">
                              <Button
                                type="button"
                                size="sm"
                                onClick={() => decide(request, "approve")}
                                disabled={reviewMutation.isPending}
                              >
                                <Check className="h-4 w-4" aria-hidden="true" />
                                Approve
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={() => decide(request, "reject")}
                                disabled={reviewMutation.isPending}
                              >
                                <X className="h-4 w-4" aria-hidden="true" />
                                Reject
                              </Button>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <ul className="space-y-3 lg:hidden">
                {requests.map((request) => (
                  <li key={request.id} className="space-y-3 rounded-lg border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">
                          {request.employee_name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {request.leave_type_name} ·{" "}
                          {formatDateRange(request.start_date, request.end_date)}{" "}
                          · {formatDays(request.days)} day
                          {request.days === 1 ? "" : "s"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Requested {requestedOn(request.created_at)}
                        </p>
                      </div>
                      <LeaveStatusBadge status={request.status} />
                    </div>

                    {request.status === "pending" ? (
                      <>
                        <label
                          htmlFor={`comment-mobile-${request.id}`}
                          className="sr-only"
                        >
                          Comment for {request.employee_name}
                        </label>
                        <Textarea
                          id={`comment-mobile-${request.id}`}
                          value={comments[request.id] ?? ""}
                          onChange={(event) =>
                            setComments((current) => ({
                              ...current,
                              [request.id]: event.target.value,
                            }))
                          }
                          placeholder="Comment (required to reject)"
                          className="min-h-[56px] text-sm"
                        />
                        <div className="flex gap-2">
                          <Button
                            type="button"
                            size="sm"
                            className="flex-1"
                            onClick={() => decide(request, "approve")}
                            disabled={reviewMutation.isPending}
                          >
                            Approve
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="flex-1"
                            onClick={() => decide(request, "reject")}
                            disabled={reviewMutation.isPending}
                          >
                            Reject
                          </Button>
                        </div>
                      </>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        {request.reviewer_name ? `${request.reviewer_name}: ` : ""}
                        {request.review_comment || "No comment"}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
