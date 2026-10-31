/** Read-only earnings/deductions breakdown used by both payroll surfaces. */

import {
  DEDUCTION_FIELDS,
  DEDUCTION_LABELS,
  EARNING_FIELDS,
  EARNING_LABELS,
  type SalaryValues,
} from "@/api/payroll";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";

type SalaryBreakdownProps = {
  values: SalaryValues & {
    adjustment_amount?: number;
    adjustment_note?: string;
  };
  className?: string;
};

function Row({ label, amount }: { label: string; amount: number }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="shrink-0 text-sm tabular-nums">{formatMoney(amount)}</dd>
    </div>
  );
}

export function SalaryBreakdown({ values, className }: SalaryBreakdownProps) {
  const adjustment = values.adjustment_amount ?? 0;

  return (
    <div className={cn("space-y-4", className)}>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border bg-muted/30 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Earnings
          </p>
          <dl>
            {EARNING_FIELDS.map((field) => (
              <Row
                key={field}
                label={EARNING_LABELS[field]}
                amount={values[field]}
              />
            ))}
            <div className="mt-2 flex items-baseline justify-between gap-3 border-t pt-2">
              <dt className="text-sm font-medium">Gross earnings</dt>
              <dd className="text-sm font-semibold tabular-nums">
                {formatMoney(values.gross_salary)}
              </dd>
            </div>
          </dl>
        </div>

        <div className="rounded-lg border bg-muted/30 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Deductions
          </p>
          <dl>
            {DEDUCTION_FIELDS.map((field) => (
              <Row
                key={field}
                label={DEDUCTION_LABELS[field]}
                amount={values[field]}
              />
            ))}
            <div className="mt-2 flex items-baseline justify-between gap-3 border-t pt-2">
              <dt className="text-sm font-medium">Total deductions</dt>
              <dd className="text-sm font-semibold tabular-nums">
                {formatMoney(values.total_deductions)}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {adjustment !== 0 ? (
        <div className="flex items-baseline justify-between gap-3 rounded-lg border bg-background px-3 py-2">
          <div className="min-w-0">
            <p className="text-sm font-medium">
              {adjustment > 0 ? "Adjustment (addition)" : "Adjustment (deduction)"}
            </p>
            {values.adjustment_note ? (
              <p className="text-xs text-muted-foreground">
                {values.adjustment_note}
              </p>
            ) : null}
          </div>
          <p className="shrink-0 text-sm font-semibold tabular-nums">
            {formatMoney(adjustment)}
          </p>
        </div>
      ) : null}

      <div className="flex items-baseline justify-between gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3">
        <p className="text-sm font-semibold">Net salary payable</p>
        <p className="text-lg font-semibold tabular-nums text-primary">
          {formatMoney(values.net_salary)}
        </p>
      </div>
    </div>
  );
}
