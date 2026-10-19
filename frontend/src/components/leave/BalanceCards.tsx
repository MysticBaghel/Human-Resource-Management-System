/** The three (or however many) leave balance boxes, shared by the pages. */

import type { LeaveBalance } from "@/api/leave";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDays } from "@/lib/format";

export function BalanceCards({ balances }: { balances: LeaveBalance[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {balances.map((balance) => {
        const percent =
          balance.allocated > 0
            ? Math.min(
                100,
                Math.round((balance.used / balance.allocated) * 100),
              )
            : 0;

        return (
          <Card key={balance.id}>
            <CardHeader className="pb-2">
              <CardDescription>{balance.leave_type_name}</CardDescription>
              <CardTitle className="text-3xl">
                {formatDays(balance.remaining)}
                <span className="ml-1 text-sm font-normal text-muted-foreground">
                  days left
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-primary"
                  style={{ width: `${percent}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                {formatDays(balance.used)} used of{" "}
                {formatDays(balance.allocated)} allocated
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
