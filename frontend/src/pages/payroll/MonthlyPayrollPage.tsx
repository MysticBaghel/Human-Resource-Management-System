/** HR/admin monthly payroll: generate, review, adjust, finalize and pay. */

import {
  Check,
  Plus,
  ReceiptText,
  Search,
  Wallet,
} from "lucide-react";
import { useState } from "react";

import { useEmployees } from "@/api/employees";
import {
  MONTH_NAMES,
  PAYMENT_STATUS_LABELS,
  PAYROLL_STATUS_LABELS,
  downloadPayslip,
  useFinalizePayroll,
  useFinalizePayrollPeriod,
  usePayrollRecords,
  type PaymentStatus,
  type PayrollRecord,
  type PayrollStatus,
} from "@/api/payroll";
import { Pagination } from "@/components/common/Pagination";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/common/states";
import { PayrollRecordsList } from "@/components/payroll/PayrollRecordsList";
import { GeneratePayrollDialog } from "@/components/payroll/GeneratePayrollDialog";
import { PaymentStatusDialog } from "@/components/payroll/PaymentStatusDialog";
import { PayrollAdjustmentDialog } from "@/components/payroll/PayrollAdjustmentDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import { formatPayPeriod } from "@/lib/format";
import { errorMessage, showError } from "@/lib/errors";
import { PAGE_SIZE } from "@/lib/query";
import { usePage } from "@/lib/usePage";

function ListSkeleton() {
  return <SkeletonRows count={6} height="h-16" label="Loading payroll records…" />;
}

function yearOptions(selected: number): number[] {
  const current = new Date().getFullYear();
  const values = new Set<number>([selected]);
  for (let year = current - 4; year <= current + 1; year += 1) {
    values.add(year);
  }
  return [...values].sort((a, b) => b - a);
}

export function MonthlyPayrollPage() {
  const today = new Date();
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [year, setYear] = useState(today.getFullYear());
  const [status, setStatus] = useState("");
  const [paymentStatus, setPaymentStatus] = useState("");
  const [search, setSearch] = useState("");
  const [generateOpen, setGenerateOpen] = useState(false);
  const [adjustRecord, setAdjustRecord] = useState<PayrollRecord | null>(null);
  const [paymentRecord, setPaymentRecord] = useState<PayrollRecord | null>(null);
  const [finalizeTarget, setFinalizeTarget] = useState<
    PayrollRecord | "period" | null
  >(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  const debouncedSearch = useDebouncedValue(search);
  const { data: employeesData } = useEmployees({ page_size: 100 });
  const finalizeMutation = useFinalizePayroll();
  const finalizePeriodMutation = useFinalizePayrollPeriod();

  const [page, setPage] = usePage(JSON.stringify([month, year, status, paymentStatus, debouncedSearch]));

  const { data, isLoading, isError, error, refetch } = usePayrollRecords({
    month,
    year,
    status: (status || undefined) as PayrollStatus | undefined,
    payment_status: (paymentStatus || undefined) as PaymentStatus | undefined,
    search: debouncedSearch || undefined,
    page,
    page_size: PAGE_SIZE,
  });

  const rows = data?.results ?? [];
  const hasFilters = Boolean(status || paymentStatus || debouncedSearch);
  const isFinalizing =
    finalizeMutation.isPending || finalizePeriodMutation.isPending;

  async function handleFinalize() {
    if (finalizeTarget === null) return;
    try {
      if (finalizeTarget === "period") {
        const result = await finalizePeriodMutation.mutateAsync({ month, year });
        toast({
          title: "Payroll finalized",
          description: `${result.finalized_count} draft record${
            result.finalized_count === 1 ? "" : "s"
          } finalized for ${formatPayPeriod(month, year)}.`,
          variant: "success",
        });
      } else {
        await finalizeMutation.mutateAsync(finalizeTarget.id);
        toast({
          title: "Payroll finalized",
          description: `${finalizeTarget.employee_name} · ${formatPayPeriod(
            finalizeTarget.payroll_month,
            finalizeTarget.payroll_year,
          )}`,
          variant: "success",
        });
      }
      setFinalizeTarget(null);
    } catch (caught) {
      showError("Could not finalize payroll", caught);
    }
  }

  async function handleDownload(record: PayrollRecord) {
    setDownloadingId(record.id);
    try {
      await downloadPayslip(record);
    } catch (caught) {
      showError("Could not download the payslip", caught);
    } finally {
      setDownloadingId(null);
    }
  }

  function clearFilters() {
    setStatus("");
    setPaymentStatus("");
    setSearch("");
    setPage(1);
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Monthly payroll</h1>
          <p className="text-sm text-muted-foreground">
            Review and adjust drafts, finalize snapshots, then record payments.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => setFinalizeTarget("period")}
            disabled={isFinalizing}
          >
            <Check className="h-4 w-4" aria-hidden="true" />
            Finalize all drafts
          </Button>
          <Button type="button" onClick={() => setGenerateOpen(true)}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Generate payroll
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="space-y-4 p-4 sm:p-6">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            <Select
              value={month}
              onChange={(event) => setMonth(Number(event.target.value))}
              aria-label="Payroll month"
            >
              {MONTH_NAMES.map((name, index) => (
                <option key={name} value={index + 1}>
                  {name}
                </option>
              ))}
            </Select>
            <Select
              value={year}
              onChange={(event) => setYear(Number(event.target.value))}
              aria-label="Payroll year"
            >
              {yearOptions(year).map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </Select>
            <div className="relative sm:col-span-2 lg:col-span-1">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search employee or payslip no."
                aria-label="Search payroll records"
                className="pl-9"
              />
            </div>
            <Select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              aria-label="Filter by payroll status"
            >
              <option value="">All payroll statuses</option>
              {(Object.keys(PAYROLL_STATUS_LABELS) as PayrollStatus[]).map(
                (value) => (
                  <option key={value} value={value}>
                    {PAYROLL_STATUS_LABELS[value]}
                  </option>
                ),
              )}
            </Select>
            <Select
              value={paymentStatus}
              onChange={(event) => setPaymentStatus(event.target.value)}
              aria-label="Filter by payment status"
            >
              <option value="">All payment statuses</option>
              {(Object.keys(PAYMENT_STATUS_LABELS) as PaymentStatus[]).map(
                (value) => (
                  <option key={value} value={value}>
                    {PAYMENT_STATUS_LABELS[value]}
                  </option>
                ),
              )}
            </Select>
          </div>

          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <ErrorState
              title="Could not load payroll records"
              message={errorMessage(error)}
              onRetry={() => void refetch()}
            />
          ) : rows.length === 0 ? (
            <EmptyState
              title={
                hasFilters
                  ? "No payroll records match these filters"
                  : `No payroll for ${formatPayPeriod(month, year)}`
              }
              description={
                hasFilters
                  ? "Try a different status or clear the filters."
                  : "Generate draft payroll from the salary structures that apply to this period."
              }
              action={
                hasFilters ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={clearFilters}
                  >
                    Clear filters
                  </Button>
                ) : (
                  <Button type="button" size="sm" onClick={() => setGenerateOpen(true)}>
                    Generate payroll
                  </Button>
                )
              }
            />
          ) : (
            <>
              <PayrollRecordsList
                rows={rows}
                downloadingId={downloadingId}
                onAdjust={setAdjustRecord}
                onFinalize={setFinalizeTarget}
                onPayment={setPaymentRecord}
                onDownload={(record) => void handleDownload(record)}
              />

              <Pagination
                page={data?.page ?? page}
                pages={data?.pages ?? 1}
                count={data?.count ?? rows.length}
                pageSize={data?.page_size ?? PAGE_SIZE}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>

      <p className="flex items-center gap-2 text-xs text-muted-foreground">
        <ReceiptText className="h-3.5 w-3.5" aria-hidden="true" />
        Finalizing freezes every salary component. Later structure revisions do
        not touch finalized or drafted records.
      </p>

      <GeneratePayrollDialog
        open={generateOpen}
        onOpenChange={setGenerateOpen}
        month={month}
        year={year}
        employees={employeesData?.results ?? []}
        onGenerated={(generatedMonth, generatedYear) => {
          setMonth(generatedMonth);
          setYear(generatedYear);
          setPage(1);
        }}
      />

      <PayrollAdjustmentDialog
        open={adjustRecord !== null}
        onOpenChange={(open) => {
          if (!open) setAdjustRecord(null);
        }}
        record={adjustRecord}
      />

      <PaymentStatusDialog
        open={paymentRecord !== null}
        onOpenChange={(open) => {
          if (!open) setPaymentRecord(null);
        }}
        record={paymentRecord}
      />

      <Dialog
        open={finalizeTarget !== null}
        onOpenChange={(open) => {
          if (!open) setFinalizeTarget(null);
        }}
        title={
          finalizeTarget === "period"
            ? `Finalize all drafts for ${formatPayPeriod(month, year)}?`
            : finalizeTarget
              ? `Finalize ${finalizeTarget.employee_name}'s payroll?`
              : "Finalize payroll"
        }
        description="Finalizing stores the salary snapshot permanently. Adjustments are no longer possible."
        footer={
          <>
            <Button
              type="button"
              variant="outline"
              onClick={() => setFinalizeTarget(null)}
              disabled={isFinalizing}
            >
              Cancel
            </Button>
            <Button type="button" onClick={() => void handleFinalize()} disabled={isFinalizing}>
              {isFinalizing ? "Finalizing…" : "Finalize"}
            </Button>
          </>
        }
      >
        <div className="flex items-start gap-3 rounded-lg border bg-muted/30 p-3">
          <Wallet className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">
            {finalizeTarget === "period"
              ? "Every draft record for this month will be finalized in one transaction."
              : "This record will be locked for salary changes. Payment status can still be recorded afterwards."}
          </p>
        </div>
      </Dialog>
    </div>
  );
}
