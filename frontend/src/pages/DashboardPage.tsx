/** Role-aware dashboard, backed by one scoped /api/v1/dashboard/ call. */

import {
  AlarmClock,
  CalendarDays,
  CalendarRange,
  ClipboardCheck,
  Users,
  UsersRound,
} from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { useDashboard } from "@/api/dashboard";
import { ROLE_LABELS, useHealth } from "@/api/queries";
import { useAuth } from "@/auth/AuthContext";
import { EmptyState, ErrorState } from "@/components/common/states";
import { ActivityList } from "@/components/dashboard/ActivityList";
import { LeaveList } from "@/components/dashboard/LeaveList";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { BalanceCards } from "@/components/leave/BalanceCards";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

function PageSkeleton() {
  return (
    <div className="mx-auto w-full max-w-6xl space-y-6" aria-busy="true" aria-live="polite">
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-28 w-full" />
        ))}
      </div>
      <Skeleton className="h-64 w-full" />
      <span className="sr-only">Loading your dashboard…</span>
    </div>
  );
}

function SystemStatus() {
  const { data, isLoading, isError, refetch } = useHealth();

  if (isLoading) {
    return <Skeleton className="h-6 w-40" />;
  }

  if (isError) {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium text-destructive">
          API unreachable
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void refetch()}
        >
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" aria-hidden="true" />
      <span className="font-medium">{data?.status ?? "unknown"}</span>
      <span className="text-xs text-muted-foreground">
        GET /api/v1/health/
      </span>
    </div>
  );
}

function SectionCard({
  title,
  description,
  action,
  children,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
        <div className="space-y-1">
          <CardTitle className="text-base">{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </div>
        {action}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading, isError, error, refetch } = useDashboard();

  if (user === null) return null;
  if (isLoading) return <PageSkeleton />;

  if (isError || data === undefined) {
    return (
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <ErrorState
          title="Could not load your dashboard"
          message={error instanceof Error ? error.message : undefined}
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const metrics = data.metrics;
  const number = (key: string) => metrics[key] ?? 0;
  const name = user.email.split("@")[0];

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            Welcome, {name}
          </h1>
          <p className="text-sm text-muted-foreground">
            {ROLE_LABELS[user.role]} dashboard · live company data
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">{ROLE_LABELS[user.role]}</Badge>
          <Button asChild variant="outline" size="sm">
            <Link to="/time-off">Time off</Link>
          </Button>
        </div>
      </div>

      {user.role === "admin" ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <MetricCard
              label="Active employees"
              value={number("active_employees")}
              href="/employees"
              icon={Users}
            />
            <MetricCard
              label="Teams"
              value={number("teams")}
              href="/teams"
              icon={UsersRound}
            />
            <MetricCard
              label="Pending leave"
              value={number("pending_leave_requests")}
              href="/approvals"
              icon={ClipboardCheck}
            />
            <MetricCard
              label="On leave today"
              value={number("on_leave_today")}
              href="/team-calendar"
              icon={CalendarDays}
            />
          </div>

          <SectionCard
            title="Recent company activity"
            description="Latest audited changes across the company."
            action={
              <Button asChild variant="ghost" size="sm">
                <Link to="/audit-log">Audit log</Link>
              </Button>
            }
          >
            <ActivityList
              entries={data.recent_activity ?? []}
              empty="No company activity yet."
            />
          </SectionCard>
        </>
      ) : null}

      {user.role === "hr" ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <MetricCard
              label="Active employees"
              value={number("active_employees")}
              href="/employees"
              icon={Users}
            />
            <MetricCard
              label="Teams"
              value={number("teams")}
              href="/teams"
              icon={UsersRound}
            />
            <MetricCard
              label="Pending leave"
              value={number("pending_leave_requests")}
              href="/approvals"
              icon={ClipboardCheck}
            />
            <MetricCard
              label="Needs HR review"
              value={number("pending_without_manager")}
              href="/approvals"
              hint="no manager assigned"
              icon={AlarmClock}
            />
            <MetricCard
              label="On leave today"
              value={number("on_leave_today")}
              href="/team-calendar"
              icon={CalendarDays}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <SectionCard
              title="Recent employee changes"
              description="New and updated people records."
            >
              <ActivityList
                entries={data.recent_employee_changes ?? []}
                empty="No employee changes yet."
              />
            </SectionCard>
            <SectionCard
              title="Recent activity"
              description="Latest audited changes."
              action={
                <Button asChild variant="ghost" size="sm">
                  <Link to="/audit-log">Audit log</Link>
                </Button>
              }
            >
              <ActivityList
                entries={data.recent_activity ?? []}
                empty="No activity yet."
              />
            </SectionCard>
          </div>
        </>
      ) : null}

      {user.role === "manager" ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <MetricCard
              label="Team members"
              value={number("team_employees")}
              href="/employees"
              icon={Users}
            />
            <MetricCard
              label="Pending approvals"
              value={number("pending_leave_requests")}
              href="/approvals"
              icon={ClipboardCheck}
            />
            <MetricCard
              label="Needs attention"
              value={number("pending_attention")}
              href="/approvals"
              hint="pending over 2 days"
              icon={AlarmClock}
            />
            <MetricCard
              label="On leave today"
              value={number("on_leave_today")}
              href="/team-calendar"
              icon={CalendarDays}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <SectionCard
              title="Pending approvals"
              description="Your team's requests waiting for a decision."
              action={
                <Button asChild variant="ghost" size="sm">
                  <Link to="/approvals">Open approvals</Link>
                </Button>
              }
            >
              <LeaveList
                requests={data.pending_requests ?? []}
                empty="Nothing waiting for your decision."
              />
            </SectionCard>
            <SectionCard
              title="Upcoming team leave"
              description="Approved leave starting in the future."
            >
              <LeaveList
                requests={data.upcoming_leave ?? []}
                empty="No upcoming approved leave."
              />
            </SectionCard>
          </div>
        </>
      ) : null}

      {user.role === "employee" ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <MetricCard
              label="Pending requests"
              value={number("pending_leave_requests")}
              href="/time-off"
              icon={ClipboardCheck}
            />
            <MetricCard
              label="Upcoming leave"
              value={number("upcoming_leave_count")}
              href="/time-off"
              icon={CalendarRange}
            />
          </div>

          <section className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-medium text-muted-foreground">
                Leave balances
              </h2>
              <Button asChild variant="ghost" size="sm">
                <Link to="/time-off">My time off</Link>
              </Button>
            </div>
            {(data.balances ?? []).length > 0 ? (
              <BalanceCards balances={data.balances ?? []} />
            ) : (
              <EmptyState
                title="No leave allocated"
                description="Ask HR to allocate balances for this year."
              />
            )}
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <SectionCard title="Pending requests">
              <LeaveList
                requests={data.pending_requests ?? []}
                empty="No pending requests."
                showEmployee={false}
              />
            </SectionCard>
            <SectionCard title="Upcoming leave">
              <LeaveList
                requests={data.upcoming_leave ?? []}
                empty="No upcoming approved leave."
                showEmployee={false}
              />
            </SectionCard>
          </div>

          <SectionCard title="Recent decisions">
            <LeaveList
              requests={data.recent_decisions ?? []}
              empty="No decisions yet."
              showEmployee={false}
            />
          </SectionCard>
        </>
      ) : null}

      <SectionCard
        title="System status"
        description="API health is kept separate from your business metrics."
      >
        <SystemStatus />
      </SectionCard>
    </div>
  );
}
