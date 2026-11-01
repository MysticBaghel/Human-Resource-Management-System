import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { InvoiceDetail } from "@/api/invoices";
import { formatDate, formatMoney } from "@/lib/format";

type InvoicePaymentsCardProps = {
  payments: InvoiceDetail["payments"];
  canRecord: boolean;
  onRecord: () => void;
};

export function InvoicePaymentsCard({ payments, canRecord, onRecord }: InvoicePaymentsCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
        <div className="space-y-1">
          <CardTitle className="text-base">Payments</CardTitle>
          <CardDescription>
            Recorded receipts. A partial payment keeps the invoice open.
          </CardDescription>
        </div>
        {canRecord ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onRecord()}
          >
            Record payment
          </Button>
        ) : null}
      </CardHeader>
      <CardContent>
        {payments.length === 0 ? (
          <EmptyState
            title="No payments recorded"
            description="When money is received, record it here to keep the balance accurate."
          />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>Reference</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments.map((payment) => (
                  <TableRow key={payment.id}>
                    <TableCell>{formatDate(payment.payment_date)}</TableCell>
                    <TableCell>{payment.method_label}</TableCell>
                    <TableCell>
                      {payment.reference || "—"}
                      {payment.note ? (
                        <p className="text-xs text-muted-foreground">
                          {payment.note}
                        </p>
                      ) : null}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(payment.amount)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
