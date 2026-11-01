import { Bell } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import type { InvoiceDetail } from "@/api/invoices";
import { formatDateTime } from "@/lib/format";

type InvoiceRemindersCardProps = {
  reminders: InvoiceDetail["reminders"];
  canRemind: boolean;
  onSend: () => void;
};

export function InvoiceRemindersCard({ reminders, canRemind, onSend }: InvoiceRemindersCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
        <div className="space-y-1">
          <CardTitle className="text-base">Payment reminders</CardTitle>
          <CardDescription>
            Reminder emails sent for this invoice, with their message.
          </CardDescription>
        </div>
        {canRemind ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onSend()}
          >
            <Bell className="h-4 w-4" aria-hidden="true" />
            Send reminder
          </Button>
        ) : null}
      </CardHeader>
      <CardContent>
        {reminders.length === 0 ? (
          <EmptyState
            title="No reminders sent"
            description="Send a reminder when the invoice is due or overdue."
          />
        ) : (
          <ul className="space-y-2">
            {reminders.map((reminder) => (
              <li key={reminder.id} className="rounded-lg border p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium">
                      {reminder.subject}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      To {reminder.recipient_email} ·{" "}
                      {formatDateTime(reminder.created_at)}
                      {reminder.provider === "gmail" ? " · Gmail" : ""}
                    </p>
                  </div>
                  <span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
                    {reminder.trigger_label}
                  </span>
                </div>
                <details className="mt-2 text-xs text-muted-foreground">
                  <summary className="cursor-pointer select-none">
                    View message
                  </summary>
                  <pre className="mt-2 whitespace-pre-wrap font-sans">
                    {reminder.message}
                  </pre>
                </details>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
