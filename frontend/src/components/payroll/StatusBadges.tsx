import { Badge } from "@/components/ui/badge";
import {
  PAYMENT_STATUS_LABELS,
  PAYROLL_STATUS_LABELS,
  type PaymentStatus,
  type PayrollStatus,
} from "@/api/payroll";

export function PayrollStatusBadge({ status }: { status: PayrollStatus }) {
  return (
    <Badge variant={status === "finalized" ? "success" : "secondary"}>
      {PAYROLL_STATUS_LABELS[status]}
    </Badge>
  );
}

export function PaymentStatusBadge({ status }: { status: PaymentStatus }) {
  const variant =
    status === "paid" ? "success" : status === "failed" ? "destructive" : "outline";
  return <Badge variant={variant}>{PAYMENT_STATUS_LABELS[status]}</Badge>;
}
