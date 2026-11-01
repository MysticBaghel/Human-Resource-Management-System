/** Loading, empty and error states shared by the list pages. */

import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

type ErrorStateProps = {
  title?: string;
  message?: string;
  onRetry?: () => void;
};

export function ErrorState({
  title = "Could not load data",
  message,
  onRetry,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-4"
    >
      <div className="space-y-1">
        <p className="text-sm font-medium text-destructive">{title}</p>
        {message ? (
          <p className="break-words text-xs text-muted-foreground">{message}</p>
        ) : null}
      </div>
      {onRetry ? (
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-10 text-center">
      <p className="text-sm font-medium">{title}</p>
      {description ? (
        <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      ) : null}
      {action}
    </div>
  );
}

type SkeletonRowsProps = {
  count: number;
  height: string;
  label: string;
};

/** Placeholder rows shown while a list loads. */
export function SkeletonRows({ count, height, label }: SkeletonRowsProps) {
  return (
    <div className="space-y-2" aria-busy="true" aria-live="polite">
      {Array.from({ length: count }).map((_, index) => (
        <Skeleton key={index} className={`${height} w-full`} />
      ))}
      <span className="sr-only">{label}</span>
    </div>
  );
}

/** Shown while the session resolves or a route chunk loads. */
export function FullPageSpinner() {
  return (
    <div
      className="flex min-h-screen items-center justify-center bg-muted"
      role="status"
      aria-live="polite"
    >
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-primary" />
        <p className="text-sm text-muted-foreground">Loading HRMS…</p>
      </div>
    </div>
  );
}
