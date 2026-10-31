import { formatMoney } from "@/lib/format";

type InvoiceTotalsProps = {
  subtotal: number;
  discount_amount: number;
  tax_rate: number;
  tax_amount: number;
  total_amount: number;
  amount_paid?: number;
  balance_due?: number;
  compact?: boolean;
};

/** The shared totals block used by the form preview and the detail page. */
export function InvoiceTotals({
  subtotal,
  discount_amount,
  tax_rate,
  tax_amount,
  total_amount,
  amount_paid,
  balance_due,
  compact = false,
}: InvoiceTotalsProps) {
  const rows = [
    { label: "Subtotal", value: subtotal },
    ...(discount_amount > 0
      ? [{ label: "Discount", value: -discount_amount }]
      : []),
    { label: `Tax (${tax_rate.toFixed(2)}%)`, value: tax_amount },
    { label: "Total", value: total_amount, strong: true },
    ...(amount_paid !== undefined
      ? [{ label: "Amount paid", value: amount_paid }]
      : []),
    ...(balance_due !== undefined
      ? [{ label: "Balance due", value: balance_due, accent: true }]
      : []),
  ];

  return (
    <div
      className={
        compact
          ? "space-y-1 text-sm"
          : "space-y-2 rounded-lg border bg-muted/20 p-3 text-sm"
      }
    >
      {rows.map((row) => (
        <div
          key={row.label}
          className={
            row.accent
              ? "flex items-center justify-between gap-4 border-t pt-2 font-semibold text-primary"
              : row.strong
                ? "flex items-center justify-between gap-4 border-t pt-2 font-semibold"
                : "flex items-center justify-between gap-4 text-muted-foreground"
          }
        >
          <span>{row.label}</span>
          <span className="tabular-nums">{formatMoney(row.value)}</span>
        </div>
      ))}
    </div>
  );
}
