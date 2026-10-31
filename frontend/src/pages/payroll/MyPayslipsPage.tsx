/** Employee portal: own salary structure, payroll history and payslips. */

import { Download, FileText, Lock } from "lucide-react";
import { useState } from "react";

import { ApiError } from "@/api/client";
import {
  downloadPayslip,
  usePayrollRecords,
  useSalaryStructures,
  type PayrollRecord,
} from "@/api/payroll";
import { Pagination } from "@/components/common/Pagination";
import { EmptyState, ErrorState } from "@/components/common/states";
import { SalaryBreakdown } from "@/components/payroll/SalaryBreakdown";
import { PaymentStatusBadge } from "@/components/payroll/StatusBadges";
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
import { toast } from "@/components/ui/toast";
import { formatDate, formatMoney } from "@/lib/format";

function PageSkeleton() {
  return (
    <div className="mx-auto w-full max-w-5xl space-y-6" aria-busy="true">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-72" />
      </div>
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-56 w-full" />
    </div>
  );
}

const PAGE_SIZE = 20;

export function MyPayslipsPage() {
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const structures = useSalaryStructures({
    mine: true,
    active: true,
    page_size: 100,
  });
  const records = usePayrollRecords({
    mine: true,
    page,
    page_size: PAGE_SIZE,
  });

  if (structures.isLoading || records.isLoading) return <PageSkeleton />;

  if (structures.isError || records.isError) {
    const failure = structures.error ?? records.error;
    return (
      <div className="mx-auto w-full max-w-5xl space-y-6">
        <h1 className="text-2xl font-semibold tracking-tight">My payslips</h1>
        <ErrorState
          title="Could not load your payroll information"
          message={failure instanceof Error ? failure.message : undefined}
          onRetry={() => {
            void structures.refetch();
            void records.refetch();
          }}
        />
      </div>
    );
  }

  const structure = structures.data?.results[0];
  const history = records.data?.results ?? [];

  async function handleDownload(record: PayrollRecord) {
    setDownloadingId(record.id);
    try {
      await downloadPayslip(record);
    } catch (caught) {
      toast({
        title: "Could not download the payslip",
        description:
          caught instanceof ApiError ? caught.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">My payslips</h1>
        <p className="text-sm text-muted-foreground">
          Your salary structure and finalized monthly payroll. Read-only.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
          <div className="space-y-1">
            <CardTitle className="text-base">Salary structure</CardTitle>
            <CardDescription>
              {structure
                ? `Effective ${formatDate(structure.effective_date)} · ${
                    structure.designation || "—"
                  }${structure.department ? ` · ${structure.department}` : ""}`
                : "Your current salary components."}
            </CardDescription>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground">
            <Lock className="h-3 w-3" aria-hidden="true" />
            Read-only
          </span>
        </CardHeader>
        <CardContent>
          {structure ? (
            <SalaryBreakdown values={structure} />
          ) : (
            <EmptyState
              title="No salary structure assigned"
              description="Ask HR to add your salary structure. It will appear here once it exists."
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Payroll history</CardTitle>
          <CardDescription>
            Finalized records only. Open the payslip PDF for the full breakdown.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <EmptyState
              title="No finalized payslips yet"
              description="When HR finalizes a payroll run, it appears here with its payment status."
            />
          ) : (
            <>
              <div className="hidden md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Pay period</TableHead>
                      <TableHead className="text-right">Gross</TableHead>
                      <TableHead className="text-right">Deductions</TableHead>
                      <TableHead className="text-right">Net</TableHead>
                      <TableHead>Payment</TableHead>
                      <TableHead className="text-right">Payslip</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.map((record) => (
                      <TableRow key={record.id}>
                        <TableCell>
                          <p className="font-medium">{record.pay_period}</p>
                          <p className="text-xs text-muted-foreground">
                            {record.payslip_number}
                          </p>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(record.gross_salary)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(record.total_deductions)}
                        </TableCell>
                        <TableCell className="text-right font-medium tabular-nums">
                          {formatMoney(record.net_salary)}
                        </TableCell>
                        <TableCell>
                          <PaymentStatusBadge status={record.payment_status} />
                          {record.payment_date ? (
                            <p className="mt-1 text-xs text-muted-foreground">
                              {formatDate(record.payment_date)}
                            </p>
                          ) : null}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => void handleDownload(record)}
                            disabled={downloadingId === record.id}
                          >
                            <Download className="h-4 w-4" aria-hidden="true" />
                            {downloadingId === record.id ? "Downloading…" : "PDF"}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <ul className="space-y-3 md:hidden">
                {history.map((record) => (
                  <li key={record.id} className="space-y-3 rounded-lg border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{record.pay_period}</p>
                        <p className="text-xs text-muted-foreground">
                          {record.payslip_number}
                        </p>
                      </div>
                      <p className="shrink-0 text-sm font-semibold tabular-nums">
                        {formatMoney(record.net_salary)}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <PaymentStatusBadge status={record.payment_status} />
                      <span className="text-xs text-muted-foreground">
                        Gross {formatMoney(record.gross_salary)} · deductions{" "}
                        {formatMoney(record.total_deductions)}
                      </span>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={() => void handleDownload(record)}
                      disabled={downloadingId === record.id}
                    >
                      <Download className="h-4 w-4" aria-hidden="true" />
                      {downloadingId === record.id ? "Downloading…" : "Download payslip"}
                    </Button>
                  </li>
                ))}
              </ul>

              <Pagination
                page={records.data?.page ?? page}
                pages={records.data?.pages ?? 1}
                count={records.data?.count ?? history.length}
                pageSize={records.data?.page_size ?? PAGE_SIZE}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>

      <p className="flex items-center gap-2 text-xs text-muted-foreground">
        <FileText className="h-3.5 w-3.5" aria-hidden="true" />
        Payslips are generated from the salary snapshot stored when payroll was
        finalized.
      </p>
    </div>
  );
}
