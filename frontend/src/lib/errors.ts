import { ApiError } from "@/api/client";
import { toast } from "@/components/ui/toast";

/** The message of an Error, or undefined for anything else. */
export function errorMessage(error: unknown): string | undefined {
  return error instanceof Error ? error.message : undefined;
}

/** Destructive toast for a failed action; shows the API's message when there is one. */
export function showError(title: string, caught: unknown) {
  toast({
    title,
    description:
      caught instanceof ApiError ? caught.message : "Please try again.",
    variant: "destructive",
  });
}
