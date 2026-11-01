/** Route guards.
 *
 * These are a UX layer only. The API is the real gate, and every endpoint
 * enforces its own permission class and role-scoped queryset.
 */

import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import type { Role } from "@/api/queries";
import { FullPageSpinner } from "@/components/common/states";
import { useAuth } from "./AuthContext";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <FullPageSpinner />;
  }

  if (!isAuthenticated) {
    // Remember where they were headed so login can send them back.
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
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
