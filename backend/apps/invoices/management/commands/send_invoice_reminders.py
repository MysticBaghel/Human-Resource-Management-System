"""Send payment reminders for invoices that are due soon or overdue.

Intended to be run from cron (or a scheduler) once a day:

    python manage.py send_invoice_reminders --days 7

The service enforces a cooldown, so running it more often than the cooldown does
not send duplicate reminders. ``--dry-run`` lists what would be sent.
"""

from django.core.management.base import BaseCommand

from apps.invoices import services


class Command(BaseCommand):
    help = "Email payment reminders for outstanding invoices due soon or overdue."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--days",
            type=int,
            default=services.REMINDER_HORIZON_DAYS,
            help=(
                "Include invoices due within this many days "
                "(overdue always included)."
            ),
        )
        parser.add_argument(
            "--cooldown-days",
            type=int,
            default=None,
            help="Skip an invoice reminded within this many days.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the invoices that would be reminded without emailing.",
        )

    def handle(self, *args, **options) -> None:
        days = options["days"]
        cooldown = options["cooldown_days"]
        dry_run = options["dry_run"]

        if days < 0:
            self.stderr.write(self.style.ERROR("--days cannot be negative."))
            return
        if cooldown is not None and cooldown < 0:
            self.stderr.write(self.style.ERROR("--cooldown-days cannot be negative."))
            return

        result = services.send_due_reminders(
            days=days, cooldown_days=cooldown, dry_run=dry_run
        )
        candidates = result["candidates"]
        if not candidates:
            self.stdout.write("No invoices need a reminder right now.")
            return

        if dry_run:
            self.stdout.write(
                f"{len(candidates)} invoice(s) would be reminded:"
            )
            for invoice in candidates:
                self.stdout.write(
                    f"  {invoice.invoice_number} · {invoice.client_name} · "
                    f"due {invoice.due_date} · {invoice.currency} "
                    f"{invoice.balance_due:,.2f}"
                )
            return

        for reminder in result["sent"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Reminded {reminder.invoice.invoice_number} at "
                    f"{reminder.recipient_email}"
                )
            )
        for failure in result["failed"]:
            self.stderr.write(
                self.style.ERROR(
                    f"Could not remind {failure['invoice_number']}: {failure['error']}"
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Sent {len(result['sent'])} reminder(s), "
                f"{len(result['failed'])} failed."
            )
        )
