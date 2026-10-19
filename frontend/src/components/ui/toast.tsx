/** Minimal toast system in the shadcn/ui idiom.
 *
 * State lives in a module-level store so `toast()` can be called from
 * anywhere, including plain async helpers outside React.
 */

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

export type ToastVariant = "default" | "success" | "destructive";

export type Toast = {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
  duration: number;
};

type ToastInput = {
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
};

const DEFAULT_DURATION = 4000;

let toasts: Toast[] = [];
const listeners = new Set<(next: Toast[]) => void>();

function emit() {
  const snapshot = [...toasts];
  listeners.forEach((listener) => listener(snapshot));
}

export function toast({
  title,
  description,
  variant = "default",
  duration = DEFAULT_DURATION,
}: ToastInput): string {
  const id = Math.random().toString(36).slice(2);
  toasts = [...toasts, { id, title, description, variant, duration }];
  emit();
  return id;
}

export function dismissToast(id: string): void {
  toasts = toasts.filter((item) => item.id !== id);
  emit();
}

export function useToastState(): Toast[] {
  const [snapshot, setSnapshot] = useState<Toast[]>(toasts);

  useEffect(() => {
    listeners.add(setSnapshot);
    setSnapshot(toasts);
    return () => {
      listeners.delete(setSnapshot);
    };
  }, []);

  return snapshot;
}

const VARIANT_CLASSES: Record<ToastVariant, string> = {
  default: "border bg-background text-foreground",
  success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  destructive: "border-destructive/40 bg-destructive/10 text-destructive",
};

function ToastCard({
  toast: item,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: (id: string) => void;
}) {
  useEffect(() => {
    if (item.duration <= 0) return;
    const timer = window.setTimeout(() => onDismiss(item.id), item.duration);
    return () => window.clearTimeout(timer);
  }, [item.id, item.duration, onDismiss]);

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "pointer-events-auto w-full max-w-sm rounded-md border p-4 shadow-lg",
        VARIANT_CLASSES[item.variant],
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm font-semibold">{item.title}</p>
          {item.description ? (
            <p className="text-sm opacity-90">{item.description}</p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => onDismiss(item.id)}
          aria-label="Dismiss notification"
          className="rounded p-1 text-xs opacity-60 transition-opacity hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

/** Mount once near the app root. */
export function Toaster() {
  const items = useToastState();

  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-[calc(100%-2rem)] flex-col gap-2 sm:w-96"
      aria-label="Notifications"
    >
      {items.map((item) => (
        <ToastCard key={item.id} toast={item} onDismiss={dismissToast} />
      ))}
    </div>
  );
}
