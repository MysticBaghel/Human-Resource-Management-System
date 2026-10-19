/** One employee: profile details, plus deactivate/reactivate for HR and admin. */

import {
  ArrowLeft,
  Briefcase,
  CalendarDays,
  Mail,
  Phone,
  ShieldCheck,
  UserRound,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import {
  EMPLOYMENT_TYPE_LABELS,
  useEmployee,
  useSetEmployeeStatus,
} from "@/api/employees";
import { ROLE_LABELS } from "@/api/queries";
import { useAuth } from "@/auth/AuthContext";
import { ErrorState } from "@/components/common/states";
import { StatusBadge } from "@/components/employees/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { formatDate, initials } from "@/lib/format";

function Detail({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="flex gap-3">
      <Icon
        className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
        aria-hidden="true"
      />
      <div className="min-w-0">
        <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </dt>
        <dd className="break-words text-sm">{value}</dd>
      </div>
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="mx-auto w-full max-w-4xl space-y-6" aria-busy="true" aria-live="polite">
      <Skeleton className="h-4 w-24" />
      <div className="flex items-center gap-4">
        <Skeleton className="h-14 w-14 rounded-full" />
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
      </div>
      <Skeleton className="h-48 w-full" />
      <span className="sr-only">Loading employee…</span>
    </div>
  );
}

export function EmployeeDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const { hasRole } = useAuth();
  const canManage = hasRole("admin", "hr");
  const { data: employee, isLoading, isError, error, refetch } = useEmployee(
    Number.isFinite(id) ? id : undefined,
  );
  const statusMutation = useSetEmployeeStatus();
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (isLoading) return <PageSkeleton />;

  if (isError || employee === undefined) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <div className="mx-auto w-full max-w-4xl space-y-6">
        <Link
          to="/employees"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Employees
        </Link>
        <ErrorState
          title={notFound ? "Employee not found" : "Could not load this employee"}
          message={
            notFound
              ? "They may have been deleted, or they are outside your team."
              : error instanceof Error
                ? error.message
                : undefined
          }
          onRetry={notFound ? undefined : () => void refetch()}
        />
      </div>
    );
  }

  function showError(title: string, caught: unknown) {
    toast({
      title,
      description:
        caught instanceof Error ? caught.message : "Please try again.",
      variant: "destructive",
    });
  }

  function handleDeactivate() {
    if (!employee) return;
    statusMutation.mutate(
      { id: employee.id, action: "deactivate" },
      {
        onSuccess: () => {
          setConfirmOpen(false);
          toast({
            title: "Employee deactivated",
            description: `${employee.full_name} can no longer sign in.`,
            variant: "success",
          });
        },
        onError: (caught) => showError("Could not deactivate", caught),
      },
    );
  }

  function handleReactivate() {
    if (!employee) return;
    statusMutation.mutate(
      { id: employee.id, action: "reactivate" },
      {
        onSuccess: () => {
          toast({
            title: "Employee reactivated",
            description: `${employee.full_name} can sign in again.`,
            variant: "success",
          });
        },
        onError: (caught) => showError("Could not reactivate", caught),
      },
    );
  }

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <Link
        to="/employees"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Employees
      </Link>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <div
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-secondary text-lg font-semibold"
            aria-hidden="true"
          >
            {initials(employee.full_name)}
          </div>
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">
                {employee.full_name}
              </h1>
              <StatusBadge status={employee.status} />
            </div>
            <p className="text-sm text-muted-foreground">
              {employee.job_title || "No job title"} · {ROLE_LABELS[employee.role]}
            </p>
          </div>
        </div>

        {canManage ? (
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline">
              <Link to={`/employees/${employee.id}/edit`}>Edit</Link>
            </Button>
            {employee.status === "active" ? (
              <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
                Deactivate
              </Button>
            ) : (
              <Button
                onClick={handleReactivate}
                disabled={statusMutation.isPending}
              >
                {statusMutation.isPending ? "Reactivating…" : "Reactivate"}
              </Button>
            )}
          </div>
        ) : null}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-5 sm:grid-cols-2">
            <Detail icon={Mail} label="Email" value={employee.email} />
            <Detail icon={Phone} label="Phone" value={employee.phone || "—"} />
            <Detail icon={Users} label="Team" value={employee.team_name ?? "No team"} />
            <Detail
              icon={UserRound}
              label="Manager"
              value={employee.manager_name ?? "No manager — HR approves leave"}
            />
            <Detail
              icon={CalendarDays}
              label="Start date"
              value={formatDate(employee.start_date)}
            />
            <Detail
              icon={Briefcase}
              label="Employment type"
              value={EMPLOYMENT_TYPE_LABELS[employee.employment_type]}
            />
            <Detail
              icon={ShieldCheck}
              label="Access role"
              value={ROLE_LABELS[employee.role]}
            />
          </dl>
        </CardContent>
      </Card>

      <Dialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={`Deactivate ${employee.full_name}?`}
        description="They lose access immediately. Their record and history are kept, and you can reactivate them later."
        footer={
          <>
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDeactivate}
              disabled={statusMutation.isPending}
            >
              {statusMutation.isPending ? "Deactivating…" : "Deactivate"}
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted-foreground">
          Deactivating is not deleting: the person stays in the audit trail and
          the employee list, and their leave history is untouched.
        </p>
      </Dialog>
    </div>
  );
}
