import { Download } from "lucide-react";

import type { PayrollRecord } from "@/api/payroll";
import {
  PaymentStatusBadge,
  PayrollStatusBadge,
} from "@/components/payroll/StatusBadges";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate, formatMoney } from "@/lib/format";

type PayrollRecordActionsProps = {
  record: PayrollRecord;
  downloading: boolean;
  onAdjust: (record: PayrollRecord) => void;
  onFinalize: (record: PayrollRecord) => void;
  onPayment: (record: PayrollRecord) => void;
  onDownload: (record: PayrollRecord) => void;
  className: string;
  buttonClassName?: string;
};

/** Drafts can be adjusted and finalized; finalized records take payments. */
function PayrollRecordActions({
  record,
  downloading,
  onAdjust,
  onFinalize,
  onPayment,
  onDownload,
  className,
  buttonClassName,
}: PayrollRecordActionsProps) {
  return (
    <div className={className}>
      {record.status === "draft" ? (
        <>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className={buttonClassName}
            onClick={() => onAdjust(record)}
          >
            Adjust
          </Button>
          <Button
            type="button"
            size="sm"
            className={buttonClassName}
            onClick={() => onFinalize(record)}
          >
            Finalize
          </Button>
        </>
      ) : (
        <>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className={buttonClassName}
            onClick={() => onPayment(record)}
          >
            Payment
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className={buttonClassName}
            onClick={() => onDownload(record)}
            disabled={downloading}
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            {downloading ? "…" : "Payslip"}
          </Button>
        </>
      )}
    </div>
  );
}

type PayrollRecordsListProps = {
  rows: PayrollRecord[];
  downloadingId: number | null;
  onAdjust: (record: PayrollRecord) => void;
  onFinalize: (record: PayrollRecord) => void;
  onPayment: (record: PayrollRecord) => void;
  onDownload: (record: PayrollRecord) => void;
};

/** Payroll records as a table on wide screens and cards on narrow ones. */
export function PayrollRecordsList({
  rows,
  downloadingId,
  onAdjust,
  onFinalize,
  onPayment,
  onDownload,
}: PayrollRecordsListProps) {
  return (
    <>
      <div className="hidden lg:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Employee</TableHead>
              <TableHead className="text-right">Gross</TableHead>
              <TableHead className="text-right">Deductions</TableHead>
              <TableHead className="text-right">Net</TableHead>
              <TableHead>Payroll</TableHead>
              <TableHead>Payment</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((record) => (
              <TableRow key={record.id} className="align-top">
                <TableCell>
                  <p className="font-medium">{record.employee_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {record.employee_code} · {record.payslip_number}
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
                  {record.adjustment_amount !== 0 ? (
                    <p className="text-xs font-normal text-muted-foreground">
                      incl. {formatMoney(record.adjustment_amount)} adjustment
                    </p>
                  ) : null}
                </TableCell>
                <TableCell>
                  <PayrollStatusBadge status={record.status} />
                  {record.finalized_at ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDate(record.finalized_at.slice(0, 10))}
                    </p>
                  ) : null}
                </TableCell>
                <TableCell>
                  <PaymentStatusBadge status={record.payment_status} />
                  {record.payment_date ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDate(record.payment_date)}
                    </p>
                  ) : null}
                </TableCell>
                <TableCell>
                  <PayrollRecordActions
                    record={record}
                    downloading={downloadingId === record.id}
                    onAdjust={onAdjust}
                    onFinalize={onFinalize}
                    onPayment={onPayment}
                    onDownload={onDownload}
                    className="flex flex-wrap justify-end gap-1"
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <ul className="space-y-3 lg:hidden">
        {rows.map((record) => (
          <li key={record.id} className="space-y-3 rounded-lg border p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">
                  {record.employee_name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {record.employee_code} · {record.payslip_number}
                </p>
              </div>
              <p className="shrink-0 text-sm font-semibold tabular-nums">
                {formatMoney(record.net_salary)}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <PayrollStatusBadge status={record.status} />
              <PaymentStatusBadge status={record.payment_status} />
              <span className="text-xs text-muted-foreground">
                Gross {formatMoney(record.gross_salary)} · deductions{" "}
                {formatMoney(record.total_deductions)}
              </span>
            </div>
            {record.adjustment_amount !== 0 ? (
              <p className="text-xs text-muted-foreground">
                Adjustment {formatMoney(record.adjustment_amount)}
                {record.adjustment_note ? ` · ${record.adjustment_note}` : ""}
              </p>
            ) : null}
            <PayrollRecordActions
              record={record}
              downloading={downloadingId === record.id}
              onAdjust={onAdjust}
              onFinalize={onFinalize}
              onPayment={onPayment}
              onDownload={onDownload}
              className="flex gap-2"
              buttonClassName="flex-1"
            />
          </li>
        ))}
      </ul>
    </>
  );
}
