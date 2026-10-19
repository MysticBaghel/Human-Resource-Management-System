import { Route, Routes } from "react-router-dom";

import { ProtectedRoute, RoleRoute } from "@/auth/guards";
import { AppShell } from "@/components/layout/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { AcceptInvitePage } from "@/pages/auth/AcceptInvitePage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { LoginPage } from "@/pages/auth/LoginPage";
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage";
import { AuditLogPage } from "@/pages/audit/AuditLogPage";
import { EmployeeDetailPage } from "@/pages/employees/EmployeeDetailPage";
import { EmployeeFormPage } from "@/pages/employees/EmployeeFormPage";
import { EmployeesPage } from "@/pages/employees/EmployeesPage";
import { TeamsPage } from "@/pages/teams/TeamsPage";
import { ApprovalsPage } from "@/pages/timeoff/ApprovalsPage";
import { EmployeeTimeOffPage } from "@/pages/timeoff/EmployeeTimeOffPage";
import { MyTimeOffPage } from "@/pages/timeoff/MyTimeOffPage";
import { TeamCalendarPage } from "@/pages/timeoff/TeamCalendarPage";

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/accept-invite" element={<AcceptInvitePage />} />

      {/* Everything inside the shell requires a session. */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />

          {/* Reading people is for HR, admin and managers (scoped by the API);
              writing is HR and admin only. */}
          <Route element={<RoleRoute allow={["admin", "hr", "manager"]} />}>
            <Route path="/employees" element={<EmployeesPage />} />
            <Route path="/employees/:id" element={<EmployeeDetailPage />} />
          </Route>

          <Route element={<RoleRoute allow={["admin", "hr"]} />}>
            <Route path="/employees/new" element={<EmployeeFormPage />} />
            <Route path="/employees/:id/edit" element={<EmployeeFormPage />} />
            <Route path="/teams" element={<TeamsPage />} />
            <Route path="/audit-log" element={<AuditLogPage />} />
          </Route>

          {/* Time off: everyone has their own page and calendar; approvals are
              for managers, HR and admin. The API scopes what each one sees. */}
          <Route path="/time-off" element={<MyTimeOffPage />} />
          <Route path="/team-calendar" element={<TeamCalendarPage />} />
          <Route element={<RoleRoute allow={["admin", "hr"]} />}>
            <Route
              path="/time-off/employees/:id"
              element={<EmployeeTimeOffPage />}
            />
          </Route>
          <Route element={<RoleRoute allow={["admin", "hr", "manager"]} />}>
            <Route path="/approvals" element={<ApprovalsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
