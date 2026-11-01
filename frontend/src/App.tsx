import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

import { ProtectedRoute, RoleRoute } from "@/auth/guards";
import { AppShell } from "@/components/layout/AppShell";
import { FullPageSpinner } from "@/components/common/states";

/** Pages are split per route so the first load only ships what it needs. */
function page<T extends Record<string, React.ComponentType>>(
  load: () => Promise<T>,
  name: keyof T,
) {
  return lazy(async () => ({ default: (await load())[name] }));
}

const DashboardPage = page(() => import("@/pages/DashboardPage"), "DashboardPage");
const NotFoundPage = page(() => import("@/pages/NotFoundPage"), "NotFoundPage");
const AcceptInvitePage = page(() => import("@/pages/auth/AcceptInvitePage"), "AcceptInvitePage");
const ForgotPasswordPage = page(() => import("@/pages/auth/ForgotPasswordPage"), "ForgotPasswordPage");
const LoginPage = page(() => import("@/pages/auth/LoginPage"), "LoginPage");
const ResetPasswordPage = page(() => import("@/pages/auth/ResetPasswordPage"), "ResetPasswordPage");
const AuditLogPage = page(() => import("@/pages/audit/AuditLogPage"), "AuditLogPage");
const ClientsPage = page(() => import("@/pages/invoices/ClientsPage"), "ClientsPage");
const InvoiceDetailPage = page(() => import("@/pages/invoices/InvoiceDetailPage"), "InvoiceDetailPage");
const InvoicesPage = page(() => import("@/pages/invoices/InvoicesPage"), "InvoicesPage");
const EmployeeDetailPage = page(() => import("@/pages/employees/EmployeeDetailPage"), "EmployeeDetailPage");
const EmployeeFormPage = page(() => import("@/pages/employees/EmployeeFormPage"), "EmployeeFormPage");
const EmployeesPage = page(() => import("@/pages/employees/EmployeesPage"), "EmployeesPage");
const MonthlyPayrollPage = page(() => import("@/pages/payroll/MonthlyPayrollPage"), "MonthlyPayrollPage");
const MyPayslipsPage = page(() => import("@/pages/payroll/MyPayslipsPage"), "MyPayslipsPage");
const PayrollDashboardPage = page(() => import("@/pages/payroll/PayrollDashboardPage"), "PayrollDashboardPage");
const SalaryStructuresPage = page(() => import("@/pages/payroll/SalaryStructuresPage"), "SalaryStructuresPage");
const TeamsPage = page(() => import("@/pages/teams/TeamsPage"), "TeamsPage");
const ApprovalsPage = page(() => import("@/pages/timeoff/ApprovalsPage"), "ApprovalsPage");
const EmployeeTimeOffPage = page(() => import("@/pages/timeoff/EmployeeTimeOffPage"), "EmployeeTimeOffPage");
const MyTimeOffPage = page(() => import("@/pages/timeoff/MyTimeOffPage"), "MyTimeOffPage");
const TeamCalendarPage = page(() => import("@/pages/timeoff/TeamCalendarPage"), "TeamCalendarPage");

export default function App() {
  return (
    <Suspense fallback={<FullPageSpinner />}>
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

            {/* Reading people is for HR, admin and managers (scoped by the
                API); writing is HR and admin only. */}
            <Route element={<RoleRoute allow={["admin", "hr", "manager"]} />}>
              <Route path="/employees" element={<EmployeesPage />} />
              <Route path="/employees/:id" element={<EmployeeDetailPage />} />
              <Route path="/approvals" element={<ApprovalsPage />} />
            </Route>

            {/* HR and admin only: people admin, audit log, invoices (company
                financial records) and payroll management. */}
            <Route element={<RoleRoute allow={["admin", "hr"]} />}>
              <Route path="/employees/new" element={<EmployeeFormPage />} />
              <Route path="/employees/:id/edit" element={<EmployeeFormPage />} />
              <Route path="/teams" element={<TeamsPage />} />
              <Route path="/audit-log" element={<AuditLogPage />} />

              <Route path="/invoices" element={<InvoicesPage />} />
              <Route path="/invoices/clients" element={<ClientsPage />} />
              <Route path="/invoices/:id" element={<InvoiceDetailPage />} />

              <Route path="/payroll" element={<PayrollDashboardPage />} />
              <Route path="/payroll/salary-structures" element={<SalaryStructuresPage />} />
              <Route path="/payroll/monthly" element={<MonthlyPayrollPage />} />

              <Route path="/time-off/employees/:id" element={<EmployeeTimeOffPage />} />
            </Route>

            {/* Everyone has their own payslips, time off and calendar. */}
            <Route path="/payroll/my" element={<MyPayslipsPage />} />
            <Route path="/time-off" element={<MyTimeOffPage />} />
            {/* HR/admin use /time-off as the Leaves directory; this is their
                own personal view, reached from the "My time off" button. */}
            <Route path="/time-off/me" element={<MyTimeOffPage personal />} />
            <Route path="/team-calendar" element={<TeamCalendarPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
