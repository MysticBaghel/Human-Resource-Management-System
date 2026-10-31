import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type MetricCardProps = {
  label: string;
  value: string | number;
  hint?: string;
  href?: string;
  icon?: LucideIcon;
};

/** A compact dashboard metric, optionally linked to the relevant list. */
export function MetricCard({ label, value, hint, href, icon: Icon }: MetricCardProps) {
  const card = (
    <Card className={cn("h-full", href && "transition-colors hover:bg-accent/50")}>
      <CardContent className="flex items-start justify-between gap-3 p-4 sm:p-5">
        <div className="min-w-0 space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="truncate text-xl font-semibold tabular-nums sm:text-2xl">
            {value}
          </p>
          {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
        </div>
        {Icon ? (
          <Icon
            className="h-5 w-5 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
        ) : null}
      </CardContent>
    </Card>
  );

  if (!href) return card;

  return (
    <Link
      to={href}
      className="block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {card}
    </Link>
  );
}
