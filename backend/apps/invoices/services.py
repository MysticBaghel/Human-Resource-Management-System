"""Invoice services: the only place invoices, payments and reminders are written.

All money is ``Decimal``. Line-item totals, discount, tax and outstanding
balance are recalculated in one helper so the invoice list, the PDF and the
payment screen can never disagree.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.organization.models import CompanyProfile

from .gmail import EmailDeliveryError, deliver_email
from .models import (
    ZERO,
    Client,
    Invoice,
    InvoiceLineItem,
    InvoiceNumberSequence,
    InvoicePayment,
    InvoiceReminder,
    money,
)
from .pdf import render_invoice_pdf

OUTSTANDING_STATUSES = (Invoice.Status.SENT, Invoice.Status.PARTIALLY_PAID)
REMINDER_HORIZON_DAYS = 7


def calculate_totals(
    lines: list[dict],
    discount_amount: Decimal,
    tax_rate: Decimal,
    amount_paid: Decimal = ZERO,
) -> dict:
    """Subtotal, discount, tax, total and balance from normalised line items."""
    subtotal = money(sum((line["amount"] for line in lines), ZERO))
    discount = money(discount_amount or ZERO)
    if discount > subtotal:
        raise ValidationError(
            {"discount_amount": ["The discount cannot be greater than the subtotal."]}
        )
    taxable = subtotal - discount
    tax = money(taxable * Decimal(tax_rate) / Decimal("100"))
    total = money(taxable + tax)
    paid = money(amount_paid or ZERO)
    if paid > total:
        raise ValidationError(
            {"amount_paid": ["The amount paid cannot be greater than the total."]}
        )
    return {
        "subtotal": subtotal,
        "discount_amount": discount,
        "tax_amount": tax,
        "total_amount": total,
        "amount_paid": paid,
        "balance_due": money(total - paid),
    }


def normalise_items(items: list) -> list[dict]:
    """Validate line input and calculate each line amount."""
    if not items:
        raise ValidationError({"items": ["An invoice needs at least one line item."]})

    normalised: list[dict] = []
    for index, item in enumerate(items):
        description = str(item.get("description", "")).strip()
        if not description:
            raise ValidationError(
                {"items": [f"Line {index + 1} needs a description."]}
            )
        try:
            quantity = money(item.get("quantity", ZERO))
            unit_price = money(item.get("unit_price", ZERO))
        except Exception as exc:  # noqa: BLE001 - bad input becomes a field error
            raise ValidationError(
                {"items": [f"Line {index + 1} has an invalid quantity or price."]}
            ) from exc
        if quantity <= ZERO:
            raise ValidationError(
                {"items": [f"Line {index + 1} needs a quantity above zero."]}
            )
        if unit_price < ZERO:
            raise ValidationError(
                {"items": [f"Line {index + 1} cannot have a negative price."]}
            )
        normalised.append(
            {
                "description": description[:255],
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": money(quantity * unit_price),
            }
        )
    return normalised


def allocate_invoice_number(issue_date: date) -> str:
    """Allocate the next INV-YYYY-NNNN number under a row lock.

    The caller owns the surrounding transaction; ``select_for_update`` keeps two
    concurrent invoice creations from receiving the same number.
    """
    year = issue_date.year
    InvoiceNumberSequence.objects.get_or_create(year=year)
    sequence = InvoiceNumberSequence.objects.select_for_update().get(year=year)
    sequence.last_number += 1
    sequence.save(update_fields=["last_number", "updated_at"])
    return f"INV-{year}-{sequence.last_number:04d}"


def client_snapshot(client: Client) -> dict:
    return {
        "client_name": client.name,
        "client_contact_name": client.contact_name,
        "client_email": client.email,
        "client_address": client.billing_address,
        "client_tax_id": client.tax_id,
    }


def line_snapshot(line: InvoiceLineItem) -> dict:
    return {
        "description": line.description,
        "quantity": str(line.quantity),
        "unit_price": str(line.unit_price),
        "amount": str(line.amount),
    }


@transaction.atomic
def create_invoice(*, actor, data: dict) -> Invoice:
    """Generate a draft invoice with its line items and calculated totals."""
    client: Client = data["client"]
    if not client.is_active:
        raise ValidationError(
            {"client": ["This client is inactive and cannot be invoiced."]}
        )

    issue_date: date = data["issue_date"]
    due_date: date = data["due_date"]
    if due_date < issue_date:
        raise ValidationError(
            {"due_date": ["The due date must be on or after the issue date."]}
        )

    lines = normalise_items(data.get("items") or [])
    tax_rate = data.get("tax_rate", ZERO)
    totals = calculate_totals(
        lines,
        data.get("discount_amount", ZERO),
        tax_rate,
    )

    invoice = Invoice(
        client=client,
        invoice_number=allocate_invoice_number(issue_date),
        issue_date=issue_date,
        due_date=due_date,
        currency=(
            data.get("currency")
            or getattr(settings, "INVOICE_DEFAULT_CURRENCY", "INR")
        ).upper(),
        reference=data.get("reference", ""),
        notes=data.get("notes", ""),
        terms=data.get("terms", ""),
        tax_rate=tax_rate,
        created_by=actor,
        **client_snapshot(client),
        **totals,
    )
    invoice._audit_extra_changes = {
        "line_items": {
            "before": [],
            "after": [
                {
                    "description": line["description"],
                    "quantity": str(line["quantity"]),
                    "unit_price": str(line["unit_price"]),
                    "amount": str(line["amount"]),
                }
                for line in lines
            ],
        }
    }
    invoice.save()

    InvoiceLineItem.objects.bulk_create(
        [
            InvoiceLineItem(
                invoice=invoice,
                position=index,
                description=line["description"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                amount=line["amount"],
            )
            for index, line in enumerate(lines)
        ]
    )
    return invoice


@transaction.atomic
def update_invoice(*, invoice: Invoice, data: dict) -> Invoice:
    """Edit a draft invoice. Sent and paid invoices are immutable."""
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if not locked.is_editable:
        raise ValidationError(
            {"detail": ["Only draft invoices can be edited."]}
        )

    before_items = [line_snapshot(line) for line in locked.items.all()]

    client: Client = data.get("client") or locked.client
    if client.pk != locked.client_id and not client.is_active:
        raise ValidationError(
            {"client": ["This client is inactive and cannot be invoiced."]}
        )

    issue_date: date = data.get("issue_date", locked.issue_date)
    due_date: date = data.get("due_date", locked.due_date)
    if issue_date.year != locked.issue_date.year:
        raise ValidationError(
            {
                "issue_date": [
                    "The issue year cannot change after the invoice number "
                    "has been allocated."
                ]
            }
        )
    if due_date < issue_date:
        raise ValidationError(
            {"due_date": ["The due date must be on or after the issue date."]}
        )

    if "items" in data:
        lines = normalise_items(data["items"])
        locked.items.all().delete()
        InvoiceLineItem.objects.bulk_create(
            [
                InvoiceLineItem(
                    invoice=locked,
                    position=index,
                    description=line["description"],
                    quantity=line["quantity"],
                    unit_price=line["unit_price"],
                    amount=line["amount"],
                )
                for index, line in enumerate(lines)
            ]
        )
    else:
        lines = [
            {
                "amount": line.amount,
            }
            for line in locked.items.all()
        ]
        if not lines:
            raise ValidationError(
                {"items": ["An invoice needs at least one line item."]}
            )

    tax_rate = data.get("tax_rate", locked.tax_rate)
    totals = calculate_totals(
        lines,
        data.get("discount_amount", locked.discount_amount),
        tax_rate,
        amount_paid=ZERO,
    )

    locked.client = client
    locked.issue_date = issue_date
    locked.due_date = due_date
    if "currency" in data:
        locked.currency = (data["currency"] or locked.currency).upper()
    for field in ("reference", "notes", "terms"):
        if field in data:
            setattr(locked, field, data[field])
    for field, value in client_snapshot(client).items():
        setattr(locked, field, value)
    locked.tax_rate = tax_rate
    for field, value in totals.items():
        setattr(locked, field, value)

    after_items = [
        line_snapshot(line) for line in locked.items.all()
    ]
    locked._audit_extra_changes = {
        "line_items": {"before": before_items, "after": after_items}
    }
    locked.save()
    return locked


def default_invoice_subject(invoice: Invoice) -> str:
    return f"Invoice {invoice.invoice_number} from {_company_name()}"


def default_invoice_message(invoice: Invoice) -> str:
    amount = f"{invoice.currency} {invoice.total_amount:,.2f}"
    due = invoice.due_date.strftime("%d %b %Y")
    lines = [
        f"Dear {invoice.client_name},",
        "",
        (
            f"Please find attached invoice {invoice.invoice_number} for {amount}, "
            f"due on {due}."
        ),
        "",
        "The PDF invoice includes the itemised charges and payment details.",
    ]
    if invoice.terms:
        lines.extend(["", invoice.terms])
    if invoice.reference:
        lines.extend(["", f"Reference: {invoice.reference}"])
    lines.extend(
        [
            "",
            "Thank you for your business.",
            "",
            _company_name(),
        ]
    )
    return "\n".join(lines)


@transaction.atomic
def send_invoice(
    *,
    invoice: Invoice,
    actor,
    recipient_email: str = "",
    subject: str = "",
    message: str = "",
) -> Invoice:
    """Email a draft invoice (with its PDF) and mark it as sent.

    The email goes through the Gmail API when OAuth 2.0 is configured, and
    through Django's email backend only in development/test fallback mode. A
    failed send leaves the invoice as a draft so it can be retried.
    """
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if locked.status != Invoice.Status.DRAFT:
        raise ValidationError(
            {"detail": ["Only a draft invoice can be sent."]}
        )

    recipient = (recipient_email or locked.client_email).strip()
    if not recipient:
        raise ValidationError(
            {"recipient_email": ["Add a billing email or enter a recipient."]}
        )

    subject = (subject or default_invoice_subject(locked)).strip()[:200]
    body = (message or default_invoice_message(locked)).strip()
    if not body:
        raise ValidationError({"message": ["An email message is required."]})

    pdf = render_invoice_pdf(locked)
    try:
        delivery = deliver_email(
            to=recipient,
            subject=subject,
            body=body,
            attachments=[
                (f"{locked.invoice_number}.pdf", pdf, "application/pdf"),
            ],
        )
    except EmailDeliveryError as exc:
        raise ValidationError({"detail": [str(exc)]}) from exc

    locked.status = Invoice.Status.SENT
    locked.sent_at = timezone.now()
    locked.sent_to = recipient
    locked.sent_via = delivery["provider"]
    locked.sent_message_id = delivery["message_id"]
    locked.save(
        update_fields=[
            "status",
            "sent_at",
            "sent_to",
            "sent_via",
            "sent_message_id",
            "updated_at",
        ]
    )
    return locked


@transaction.atomic
def cancel_invoice(*, invoice: Invoice) -> Invoice:
    """Cancel a draft or sent invoice that has no recorded payment."""
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if not locked.can_cancel:
        raise ValidationError(
            {
                "detail": [
                    "Only a draft or sent invoice with no payments can be cancelled."
                ]
            }
        )
    locked.status = Invoice.Status.CANCELLED
    locked.cancelled_at = timezone.now()
    locked.save(update_fields=["status", "cancelled_at", "updated_at"])
    return locked


@transaction.atomic
def record_payment(
    *,
    invoice: Invoice,
    amount: Decimal,
    payment_date: date,
    method: str,
    reference: str,
    note: str,
    actor,
) -> tuple[Invoice, InvoicePayment]:
    """Record a payment and update the invoice's status and balance."""
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if not locked.is_outstanding:
        raise ValidationError(
            {"detail": ["This invoice is not open for payment."]}
        )

    amount = money(amount)
    if amount <= ZERO:
        raise ValidationError({"amount": ["Enter a payment amount above zero."]})
    if amount > locked.balance_due:
        raise ValidationError(
            {"amount": ["The payment cannot be greater than the balance due."]}
        )

    payment = InvoicePayment.objects.create(
        invoice=locked,
        amount=amount,
        payment_date=payment_date,
        method=method,
        reference=reference.strip(),
        note=note.strip(),
        recorded_by=actor,
    )

    locked.amount_paid = money(locked.amount_paid + amount)
    locked.balance_due = money(locked.total_amount - locked.amount_paid)
    if locked.balance_due == ZERO:
        locked.status = Invoice.Status.PAID
        locked.paid_at = timezone.now()
    else:
        locked.status = Invoice.Status.PARTIALLY_PAID
    locked.save(
        update_fields=[
            "amount_paid",
            "balance_due",
            "status",
            "paid_at",
            "updated_at",
        ]
    )
    return locked, payment


def _company_name() -> str:
    profile = CompanyProfile.load()
    if profile is not None and profile.name:
        return profile.name
    return getattr(settings, "PAYROLL_COMPANY_NAME", "HRMS")


def default_reminder_message(invoice: Invoice) -> str:
    """A plain-text reminder with the amount, due date and payment terms."""
    due = invoice.due_date.strftime("%d %b %Y")
    amount = f"{invoice.currency} {invoice.balance_due:,.2f}"
    lines = [
        f"Dear {invoice.client_name},",
        "",
        (
            f"This is a reminder that invoice {invoice.invoice_number} for "
            f"{amount} is still outstanding."
        ),
        (
            f"It was issued on {invoice.issue_date.strftime('%d %b %Y')} and "
            f"was due on {due}."
        ),
    ]
    if invoice.is_overdue:
        lines.append(f"The invoice is now {invoice.days_overdue} day(s) overdue.")
    if invoice.terms:
        lines.extend(["", invoice.terms])
    lines.extend(
        [
            "",
            "If payment has already been made, please disregard this message.",
            "",
            "Thank you,",
            _company_name(),
        ]
    )
    return "\n".join(lines)


@transaction.atomic
def send_invoice_reminder(
    *,
    invoice: Invoice,
    actor,
    recipient_email: str = "",
    subject: str = "",
    message: str = "",
    trigger: str = InvoiceReminder.Trigger.MANUAL,
    force: bool = False,
) -> InvoiceReminder:
    """Email a payment reminder and keep a record of who received it.

    No gateway or payment link is generated. Reminders are only allowed while
    the invoice has an outstanding balance, and the cooldown is enforced by the
    service rather than only by the UI.
    """
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if not locked.is_outstanding:
        raise ValidationError(
            {"detail": ["Only an outstanding invoice can be reminded."]}
        )
    if trigger not in InvoiceReminder.Trigger.values:
        raise ValidationError({"trigger": ["Unknown reminder trigger."]})
    if not force and not locked.reminder_due:
        raise ValidationError(
            {
                "detail": [
                    "A reminder was sent recently. Wait for the cooldown "
                    "period before sending another."
                ]
            }
        )

    recipient = (recipient_email or locked.client_email).strip()
    if not recipient:
        raise ValidationError(
            {"recipient_email": ["Add a billing email or enter a recipient."]}
        )

    subject = (subject or f"Payment reminder: {locked.invoice_number}").strip()[:200]
    body = (message or default_reminder_message(locked)).strip()
    if not body:
        raise ValidationError({"message": ["A reminder message is required."]})

    try:
        delivery = deliver_email(
            to=recipient,
            subject=subject,
            body=body,
        )
    except EmailDeliveryError as exc:
        raise ValidationError({"detail": [str(exc)]}) from exc

    reminder = InvoiceReminder.objects.create(
        invoice=locked,
        recipient_email=recipient,
        subject=subject,
        message=body,
        trigger=trigger,
        provider=delivery["provider"],
        message_id=delivery["message_id"],
        sent_by=actor,
    )
    locked.reminder_count += 1
    locked.last_reminded_at = timezone.now()
    locked.save(
        update_fields=["reminder_count", "last_reminded_at", "updated_at"]
    )
    return reminder


def reminder_candidates(
    *, days: int = REMINDER_HORIZON_DAYS, cooldown_days: int | None = None
) -> list[Invoice]:
    """Outstanding invoices due within ``days``, including already-overdue ones.

    A candidate is only returned when the cooldown has elapsed, so running the
    scheduled command twice in one day does not spam the client.
    """
    if days < 0:
        raise ValidationError({"days": ["Days cannot be negative."]})
    if cooldown_days is None:
        cooldown_days = int(getattr(settings, "INVOICE_REMINDER_COOLDOWN_DAYS", 3))

    today = timezone.localdate()
    horizon = today + timedelta(days=days)
    queryset = (
        Invoice.objects.filter(
            status__in=OUTSTANDING_STATUSES,
            balance_due__gt=ZERO,
            due_date__lte=horizon,
        )
        .exclude(client_email="")
        .order_by("due_date", "id")
    )

    now = timezone.now()
    candidates: list[Invoice] = []
    for invoice in queryset:
        if invoice.last_reminded_at is not None:
            elapsed = now - invoice.last_reminded_at
            if elapsed < timedelta(days=cooldown_days):
                continue
        candidates.append(invoice)
    return candidates


def send_due_reminders(
    *,
    days: int = REMINDER_HORIZON_DAYS,
    cooldown_days: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Send reminders for every due/overdue invoice, continuing after failures."""
    candidates = reminder_candidates(days=days, cooldown_days=cooldown_days)
    if dry_run:
        return {"candidates": candidates, "sent": [], "failed": [], "dry_run": True}

    sent: list[InvoiceReminder] = []
    failed: list[dict] = []
    for invoice in candidates:
        trigger = (
            InvoiceReminder.Trigger.OVERDUE
            if invoice.due_date < timezone.localdate()
            else InvoiceReminder.Trigger.DUE_SOON
        )
        try:
            sent.append(
                send_invoice_reminder(
                    invoice=invoice,
                    actor=None,
                    trigger=trigger,
                )
            )
        except Exception as exc:  # noqa: BLE001 - report one failure, keep going
            failed.append(
                {
                    "invoice": invoice.pk,
                    "invoice_number": invoice.invoice_number,
                    "error": str(exc),
                }
            )
    return {
        "candidates": candidates,
        "sent": sent,
        "failed": failed,
        "dry_run": False,
    }


def _total(queryset) -> Decimal:
    value = queryset.aggregate(value=Sum("balance_due"))["value"]
    return money(value or ZERO)


def build_invoice_dashboard() -> dict:
    """Receivable metrics for the invoice dashboard."""
    today = timezone.localdate()
    outstanding = Invoice.objects.filter(
        status__in=OUTSTANDING_STATUSES, balance_due__gt=ZERO
    )
    overdue = outstanding.filter(due_date__lt=today)
    due_soon = outstanding.filter(
        due_date__gte=today, due_date__lte=today + timedelta(days=REMINDER_HORIZON_DAYS)
    )

    payments = InvoicePayment.objects.filter(
        payment_date__year=today.year, payment_date__month=today.month
    )
    collected = payments.aggregate(value=Sum("amount"))["value"] or ZERO

    recent = (
        Invoice.objects.select_related("client")
        .annotate(items_count=Count("items"))
        .order_by("-issue_date", "-id")[:6]
    )

    return {
        "as_of": today.isoformat(),
        "active_clients": Client.objects.filter(is_active=True).count(),
        "total_invoices": Invoice.objects.count(),
        "draft_count": Invoice.objects.filter(status=Invoice.Status.DRAFT).count(),
        "outstanding_count": outstanding.count(),
        "outstanding_amount": str(_total(outstanding)),
        "overdue_count": overdue.count(),
        "overdue_amount": str(_total(overdue)),
        "due_soon_count": due_soon.count(),
        "due_soon_amount": str(_total(due_soon)),
        "collected_this_month": str(money(collected)),
        "payments_this_month": payments.count(),
        "reminders_sent_this_month": InvoiceReminder.objects.filter(
            created_at__year=today.year, created_at__month=today.month
        ).count(),
        "reminder_queue_count": len(reminder_candidates()),
        "recent_invoices": recent,
    }
