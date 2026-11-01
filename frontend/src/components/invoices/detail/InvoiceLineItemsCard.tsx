import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { InvoiceDetail } from "@/api/invoices";
import { formatMoney } from "@/lib/format";

type InvoiceLineItemsCardProps = { items: InvoiceDetail["items"] };

export function InvoiceLineItemsCard({ items }: InvoiceLineItemsCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Line items</CardTitle>
        <CardDescription>
          Every amount is snapshotted on the invoice.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="hidden sm:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Rate</TableHead>
                <TableHead className="text-right">Amount</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">
                    {item.description}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {item.quantity}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(item.unit_price)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(item.amount)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <ul className="space-y-2 sm:hidden">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex items-start justify-between gap-3 rounded-lg border p-3"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium">{item.description}</p>
                <p className="text-xs text-muted-foreground">
                  {item.quantity} × {formatMoney(item.unit_price)}
                </p>
              </div>
              <p className="shrink-0 text-sm font-medium tabular-nums">
                {formatMoney(item.amount)}
              </p>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
