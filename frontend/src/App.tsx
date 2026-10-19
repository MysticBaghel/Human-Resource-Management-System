import { Route, Routes } from "react-router-dom";

import { ProtectedRoute, RoleRoute } from "@/auth/guards";
import { AppShell } from "@/components/layout/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { AcceptInvitePage } from "@/pages/auth/AcceptInvitePage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { LoginPage } from "@/pages/auth/LoginPage";
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage";
import { EmployeeDetailPage } from "@/pages/employees/EmployeeDetailPage";
import { EmployeeFormPage } from "@/pages/employees/EmployeeFormPage";
import { EmployeesPage } from "@/pages/employees/EmployeesPage";
import { TeamsPage } from "@/pages/teams/TeamsPage";

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
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
