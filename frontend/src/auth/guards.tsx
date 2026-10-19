/** Route guards.
 *
 * These are a UX layer only. The API is the real gate, and every endpoint
 * enforces its own permission class and role-scoped queryset.
 */

import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import type { Role } from "@/api/queries";
import { useAuth } from "./AuthContext";

function FullPageSpinner() {
  return (
    <div
      className="flex min-h-screen items-center justify-center bg-muted"
      role="status"
      aria-live="polite"
    >
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-primary" />
        <p className="text-sm text-muted-foreground">Loading HRMS…</p>
      </div>
    </div>
  );
}

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <FullPageSpinner />;
  }

  if (!isAuthenticated) {
    // Remember where they were headed so login can send them back.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}

type RoleRouteProps = {
  allow: Role[];
  children?: ReactNode;
};

export function RoleRoute({ allow, children }: RoleRouteProps) {
  const { hasRole, isLoading } = useAuth();

  if (isLoading) {
    return <FullPageSpinner />;
  }

  if (!hasRole(...allow)) {
    return <Navigate to="/" replace />;
  }

  return <>{children ?? <Outlet />}</>;
}
