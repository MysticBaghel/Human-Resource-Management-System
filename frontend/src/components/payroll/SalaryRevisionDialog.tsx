/** Salary revision history for one employee. */

import { useSalaryRevisions, type SalarySnapshot } from "@/api/payroll";
import { EmptyState, ErrorState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime, formatMoney } from "@/lib/format";

type MoneySnapshotKey = Exclude<
  keyof SalarySnapshot,
  "effective_date" | "is_active"
>;

const TRACKED_FIELDS: { key: MoneySnapshotKey; label: string }[] = [
  { key: "basic_salary", label: "Basic salary" },
  { key: "hra", label: "HRA" },
  { key: "conveyance_allowance", label: "Conveyance" },
  { key: "medical_allowance", label: "Medical" },
  { key: "special_allowance", label: "Special allowance" },
  { key: "other_allowances", label: "Other allowances" },
  { key: "provident_fund", label: "PF" },
  { key: "professional_tax", label: "Professional tax" },
  { key: "income_tax", label: "Income tax / TDS" },
  { key: "other_deductions", label: "Other deductions" },
  { key: "gross_salary", label: "Gross salary" },
  { key: "total_deductions", label: "Total deductions" },
  { key: "net_salary", label: "Net salary" },
];

function changedFields(previous: SalarySnapshot, next: SalarySnapshot) {
  return TRACKED_FIELDS.filter(
    ({ key }) => String(previous[key]) !== String(next[key]),
  );
}

type SalaryRevisionDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  employee: number | null;
  employeeName?: string;
};

export function SalaryRevisionDialog({
  open,
  onOpenChange,
  employee,
  employeeName,
}: SalaryRevisionDialogProps) {
  const { data, isLoading, isError, error, refetch } = useSalaryRevisions(
    open && employee !== null ? employee : undefined,
  );
  const revisions = data?.results ?? [];

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={employeeName ? `Revision history · ${employeeName}` : "Revision history"}
      description="Previous and updated values, who made the change, and when it took effect."
      className="sm:max-w-3xl"
      footer={
        <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
          Close
        </Button>
      }
    >
      <div className="space-y-3">
        {isLoading ? (
          <div className="space-y-2" aria-busy="true">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : isError ? (
          <ErrorState
            title="Could not load revision history"
            message={error instanceof Error ? error.message : undefined}
            onRetry={() => void refetch()}
          />
        ) : revisions.length === 0 ? (
          <EmptyState
            title="No revisions yet"
            description="Changing this salary structure will add the first revision here."
          />
        ) : (
          revisions.map((revision) => {
            const changes = changedFields(
              revision.previous_values,
              revision.new_values,
            );
            return (
              <article key={revision.id} className="rounded-lg border p-4">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-sm font-medium">
                      Effective {revision.effective_date}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {revision.updated_by_email ?? "System"} ·{" "}
                      {formatDateTime(revision.created_at)}
                    </p>
                  </div>
                  {revision.reason ? (
                    <p className="text-xs text-muted-foreground sm:max-w-[55%] sm:text-right">
                      {revision.reason}
                    </p>
                  ) : null}
                </div>

                <div className="mt-3 space-y-1">
                  {changes.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Effective date updated; component values unchanged.
                    </p>
                  ) : (
                    changes.map(({ key, label }) => (
                      <div
                        key={key}
                        className="flex flex-col justify-between gap-1 border-t py-1 text-sm first:border-t-0 sm:flex-row sm:items-center"
                      >
                        <span className="text-muted-foreground">{label}</span>
                        <span className="tabular-nums">
                          {formatMoney(revision.previous_values[key])} →{" "}
                          <span className="font-medium">
                            {formatMoney(revision.new_values[key])}
                          </span>
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </article>
            );
          })
        )}
      </div>
    </Dialog>
  );
}
