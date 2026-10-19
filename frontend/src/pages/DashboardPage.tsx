/** Landing page after login. Confirms the session and shows the user's role. */

import { useAuth } from "@/auth/AuthContext";
import { ROLE_LABELS, useHealth, type Role } from "@/api/queries";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const ROLE_SCOPE: Record<Role, string> = {
  admin: "Full access, including roles and settings.",
  hr: "All employees and teams, leave types, and every leave request.",
  manager: "Your own team: view members, approve or reject their leave.",
  employee: "Your own profile and your own time off.",
};

function HealthCard() {
  const { data, isError, isLoading, refetch, isFetching, error } = useHealth();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">API status</CardTitle>
        <CardDescription>GET /api/v1/health/</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2" aria-busy="true" aria-live="polite">
            <div className="h-6 w-20 animate-pulse rounded bg-muted" />
            <div className="h-3 w-40 animate-pulse rounded bg-muted" />
            <span className="sr-only">Checking API status…</span>
          </div>
        ) : isError ? (
          <div className="space-y-3" role="alert">
            <p className="text-sm font-medium text-destructive">
              Could not reach the API
            </p>
            <p className="break-words text-xs text-muted-foreground">
              {error instanceof Error ? error.message : "Unknown error."}
            </p>
            <button
              type="button"
              onClick={() => void refetch()}
              disabled={isFetching}
              className="inline-flex items-center rounded-md border border-input px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent disabled:opacity-60"
            >
              {isFetching ? "Retrying…" : "Retry"}
            </button>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-emerald-100 px-3 py-1 text-sm font-semibold text-emerald-800">
              {data?.status ?? "unknown"}
            </span>
            <span className="text-xs text-muted-foreground">Django is responding</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { user } = useAuth();

  if (user === null) return null;

  const name = user.email.split("@")[0];

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Welcome, {name}</h1>
        <p className="text-sm text-muted-foreground">
          You are signed in as{" "}
          <span className="font-medium text-foreground">{ROLE_LABELS[user.role]}</span>.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Signed in</CardTitle>
            <CardDescription>{user.email}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">Role</span>
              <span className="inline-flex items-center rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium">
                {ROLE_LABELS[user.role]}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">Status</span>
              <span className="font-medium">{user.is_active ? "Active" : "Inactive"}</span>
            </div>
          </CardContent>
        </Card>

        <HealthCard />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">What this role can do</CardTitle>
          <CardDescription>
            The API enforces this. The sidebar only reflects it.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {ROLE_SCOPE[user.role]}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Coming next</CardTitle>
          <CardDescription>Phase 3 and later</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
            <li>Time off: requests, approvals, balances and a team calendar</li>
            <li>Polish pass with demo data</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
