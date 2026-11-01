/** HR/admin payroll dashboard: current month totals and recent activity. */

import {
  ArrowRight,
  Banknote,
  Clock,
  ReceiptText,
  Users,
  Wallet,
} from "lucide-react";
import { Link } from "react-router-dom";

import { usePayrollDashboard } from "@/api/payroll";
import { EmptyState, ErrorState } from "@/components/common/states";
import { PayrollMetricCard } from "@/components/payroll/PayrollMetricCard";
import { PaymentStatusBadge, PayrollStatusBadge } from "@/components/payroll/StatusBadges";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney, formatPayPeriod } from "@/lib/format";
import { errorMessage } from "@/lib/errors";

function PageSkeleton() {
  return (
    <div className="mx-auto w-full max-w-6xl space-y-6" aria-busy="true">
      <div className="space-y-2">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-80" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-28 w-full" />
        ))}
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

export function PayrollDashboardPage() {
  const { data, isLoading, isError, error, refetch } = usePayrollDashboard();

  if (isLoading) return <PageSkeleton />;

  if (isError || data === undefined) {
    return (
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <h1 className="text-2xl font-semibold tracking-tight">Payroll</h1>
        <ErrorState
          title="Could not load the payroll dashboard"
          message={errorMessage(error)}
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const period = formatPayPeriod(data.month, data.year);
  const recent = data.recent_activity ?? [];

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Payroll</h1>
          <p className="text-sm text-muted-foreground">
            {period} · salary structures, pay runs and payments.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/payroll/salary-structures">Salary structures</Link>
          </Button>
          <Button asChild size="sm">
            <Link to="/payroll/monthly">
              Monthly payroll
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <PayrollMetricCard
          label="With a salary structure"
          value={data.employees_with_salary_structures}
          hint="Active structures"
          href="/payroll/salary-structures"
          icon={Users}
        />
        <PayrollMetricCard
          label={`${period} payroll`}
          value={formatMoney(data.current_month_payroll_total)}
          hint="Net payable, all records"
          href="/payroll/monthly"
          icon={Wallet}
        />
        <PayrollMetricCard
          label="Paid this month"
          value={formatMoney(data.total_paid_amount)}
          hint={`${data.finalized_count} finalized records`}
          icon={Banknote}
        />
        <PayrollMetricCard
          label="Pending payments"
          value={data.pending_payments_count}
          hint={formatMoney(data.pending_payments_amount)}
          icon={Clock}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Draft records
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">
              {data.draft_count}
            </p>
            <p className="text-xs text-muted-foreground">
              Adjust and finalize before paying.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Finalized records
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">
              {data.finalized_count}
            </p>
            <p className="text-xs text-muted-foreground">
              Salary values are frozen as snapshots.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Failed payments
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">
              {data.failed_payments_count}
            </p>
            <p className="text-xs text-muted-foreground">
              Update the status after resolving.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
          <div className="space-y-1">
            <CardTitle className="text-base">Recent payroll activity</CardTitle>
            <CardDescription>
              Latest pay runs and payment updates across the company.
            </CardDescription>
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link to="/payroll/monthly">Open monthly payroll</Link>
          </Button>
        </CardHeader>
        <CardContent>
          {recent.length === 0 ? (
            <EmptyState
              title="No payroll yet"
              description="Create salary structures, then generate this month's payroll."
              action={
                <Button asChild size="sm">
                  <Link to="/payroll/salary-structures">Set up salaries</Link>
                </Button>
              }
            />
          ) : (
            <>
              <div className="hidden md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead>Period</TableHead>
                      <TableHead className="text-right">Net pay</TableHead>
                      <TableHead>Payroll</TableHead>
                      <TableHead>Payment</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recent.map((record) => (
                      <TableRow key={record.id}>
                        <TableCell>
                          <p className="font-medium">{record.employee_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {record.employee_code}
                          </p>
                        </TableCell>
                        <TableCell>{record.pay_period}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(record.net_salary)}
                        </TableCell>
                        <TableCell>
                          <PayrollStatusBadge status={record.status} />
                        </TableCell>
                        <TableCell>
                          <PaymentStatusBadge status={record.payment_status} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <ul className="space-y-2 md:hidden">
                {recent.map((record) => (
                  <li key={record.id} className="rounded-lg border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">
                          {record.employee_name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {record.pay_period} · {formatMoney(record.net_salary)}
                        </p>
                      </div>
                      <PaymentStatusBadge status={record.payment_status} />
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardContent>
      </Card>

      <p className="flex items-center gap-2 text-xs text-muted-foreground">
        <ReceiptText className="h-3.5 w-3.5" aria-hidden="true" />
        Payslips use the company profile in the Django admin; employees download
        their own finalized payslips from My payslips.
      </p>
    </div>
  );
}
