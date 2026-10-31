"""Client invoices: receivable invoices, payments, reminders and uploads.

Invoices are issued by the company to a client. Every amount is a ``Decimal``
and the client details plus the totals are snapshotted onto the invoice row, so
editing a client later never rewrites an invoice that has already been sent.
"""

import uuid
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

MONEY_MAX_DIGITS = 12
MONEY_DECIMAL_PLACES = 2
ZERO = Decimal("0.00")
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


def money_field(label: str, **kwargs) -> models.DecimalField:
    """A non-negative monetary column with the project-wide precision."""
    return models.DecimalField(
        label,
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=ZERO,
        validators=[MinValueValidator(ZERO)],
        **kwargs,
    )


def money(value) -> Decimal:
    """Round a value to two decimal places using normal financial rounding."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def invoice_upload_path(instance, filename: str) -> str:
    """Keep uploads in a year folder with an unguessable name.

    The original filename is stored separately on the row; the on-disk name
    never has to be trusted as a path.
    """
    suffix = Path(filename).suffix.lower()[:10]
    year = instance.invoice.issue_date.year if instance.invoice_id else "unknown"
    return f"invoices/{year}/{uuid.uuid4().hex}{suffix}"


class Client(models.Model):
    """A company or person the company bills."""

    name = models.CharField(_("client name"), max_length=200)
    contact_name = models.CharField(_("contact name"), max_length=160, blank=True)
    email = models.EmailField(_("billing email"), blank=True)
    phone = models.CharField(_("phone"), max_length=40, blank=True)
    billing_address = models.TextField(_("billing address"), blank=True)
    tax_id = models.CharField(
        _("tax id / GSTIN"),
        max_length=40,
        blank=True,
        help_text=_("Printed on the invoice when set."),
    )
    notes = models.TextField(_("notes"), blank=True)
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Inactive clients stay on old invoices but cannot be billed."),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("client")
        verbose_name_plural = _("clients")
        indexes = [models.Index(fields=["is_active", "name"])]

    def __str__(self) -> str:
        return self.name

    @property
    def code(self) -> str:
        return f"CLI-{self.pk:04d}" if self.pk else "CLI-0000"


class InvoiceNumberSequence(models.Model):
    """The last invoice number allocated in a year.

    A row is locked in a transaction while a number is allocated, so two
    concurrent invoice creations can never receive the same number.
    """

    year = models.PositiveSmallIntegerField(_("year"), unique=True)
    last_number = models.PositiveIntegerField(_("last number"), default=0)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("invoice number sequence")
        verbose_name_plural = _("invoice number sequences")

    def __str__(self) -> str:
        return f"{self.year}: {self.last_number}"


class Invoice(models.Model):
    """One invoice issued to a client.

    ``subtotal`` through ``balance_due`` are snapshots calculated from the line
    items, discount and tax rate. Payments update ``amount_paid`` and
    ``balance_due`` in the same transaction that writes the payment row.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SENT = "sent", _("Sent")
        PARTIALLY_PAID = "partially_paid", _("Partially paid")
        PAID = "paid", _("Paid")
        CANCELLED = "cancelled", _("Cancelled")

    client = models.ForeignKey(
        Client,
        verbose_name=_("client"),
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    invoice_number = models.CharField(_("invoice number"), max_length=32, unique=True)
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    issue_date = models.DateField(_("issue date"))
    due_date = models.DateField(_("due date"))
    currency = models.CharField(
        _("currency"),
        max_length=3,
        default="INR",
        help_text=_("Three-letter currency code, for example INR."),
    )
    reference = models.CharField(
        _("reference / PO number"),
        max_length=100,
        blank=True,
        help_text=_("Optional purchase order or client reference."),
    )
    notes = models.TextField(_("notes"), blank=True)
    terms = models.TextField(_("payment terms"), blank=True)

    # The client's details are copied when the invoice is issued. Changing the
    # client record afterwards must not rewrite an old invoice.
    client_name = models.CharField(_("client name"), max_length=200)
    client_contact_name = models.CharField(
        _("client contact"), max_length=160, blank=True
    )
    client_email = models.EmailField(_("client email"), blank=True)
    client_address = models.TextField(_("client address"), blank=True)
    client_tax_id = models.CharField(_("client tax id"), max_length=40, blank=True)

    subtotal = money_field(_("subtotal"))
    discount_amount = money_field(_("discount"))
    tax_rate = models.DecimalField(
        _("tax rate (%)"),
        max_digits=5,
        decimal_places=2,
        default=ZERO,
        validators=[MinValueValidator(ZERO), MaxValueValidator(Decimal("100.00"))],
    )
    tax_amount = money_field(_("tax amount"))
    total_amount = money_field(_("total amount"))
    amount_paid = money_field(_("amount paid"))
    balance_due = money_field(_("balance due"))

    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    sent_to = models.EmailField(_("sent to"), blank=True)
    sent_via = models.CharField(
        _("sent via"), max_length=20, blank=True
    )
    sent_message_id = models.CharField(_("sent message id"), max_length=255, blank=True)
    paid_at = models.DateTimeField(_("paid at"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)
    last_reminded_at = models.DateTimeField(
        _("last reminded at"), null=True, blank=True
    )
    reminder_count = models.PositiveIntegerField(_("reminder count"), default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("created by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_invoices",
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ["-issue_date", "-id"]
        verbose_name = _("invoice")
        verbose_name_plural = _("invoices")
        constraints = [
            models.CheckConstraint(
                condition=Q(due_date__gte=F("issue_date")),
                name="invoice_due_date_on_or_after_issue_date",
            ),
            models.CheckConstraint(
                condition=(
                    Q(subtotal__gte=0)
                    & Q(discount_amount__gte=0)
                    & Q(tax_rate__gte=0)
                    & Q(tax_rate__lte=100)
                    & Q(tax_amount__gte=0)
                    & Q(total_amount__gte=0)
                    & Q(amount_paid__gte=0)
                    & Q(balance_due__gte=0)
                ),
                name="invoice_amounts_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(discount_amount__lte=F("subtotal")),
                name="invoice_discount_not_above_subtotal",
            ),
            models.CheckConstraint(
                condition=Q(amount_paid__lte=F("total_amount")),
                name="invoice_paid_not_above_total",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["client", "-issue_date"]),
            models.Index(fields=["-issue_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.invoice_number} · {self.client_name}"

    @property
    def is_editable(self) -> bool:
        return self.status == self.Status.DRAFT

    @property
    def is_outstanding(self) -> bool:
        return (
            self.status in {self.Status.SENT, self.Status.PARTIALLY_PAID}
            and self.balance_due > ZERO
        )

    @property
    def is_overdue(self) -> bool:
        return self.is_outstanding and self.due_date < timezone.localdate()

    @property
    def days_overdue(self) -> int:
        if not self.is_overdue:
            return 0
        return (timezone.localdate() - self.due_date).days

    @property
    def reminder_cooldown_days(self) -> int:
        return int(getattr(settings, "INVOICE_REMINDER_COOLDOWN_DAYS", 3))

    @property
    def reminder_due(self) -> bool:
        """Whether a payment reminder is allowed by the cooldown policy."""
        if not self.is_outstanding:
            return False
        if self.last_reminded_at is None:
            return True
        elapsed = timezone.now() - self.last_reminded_at
        return elapsed.days >= self.reminder_cooldown_days

    @property
    def can_send_reminder(self) -> bool:
        return self.reminder_due and bool(self.client_email.strip())

    @property
    def can_record_payment(self) -> bool:
        return self.is_outstanding

    @property
    def can_cancel(self) -> bool:
        return self.status in {self.Status.DRAFT, self.Status.SENT} and (
            self.amount_paid == ZERO
        )

    def recalculate(self) -> None:
        """Recompute totals from the current line items and payment total."""
        line_total = sum(
            (line.amount for line in self.items.all()),
            ZERO,
        )
        self.subtotal = money(line_total)
        if self.discount_amount > self.subtotal:
            self.discount_amount = self.subtotal
        taxable = self.subtotal - self.discount_amount
        self.tax_amount = money(taxable * self.tax_rate / Decimal("100"))
        self.total_amount = money(taxable + self.tax_amount)
        self.amount_paid = money(self.amount_paid)
        self.balance_due = money(self.total_amount - self.amount_paid)


class InvoiceLineItem(models.Model):
    """One billed line on an invoice."""

    invoice = models.ForeignKey(
        Invoice,
        verbose_name=_("invoice"),
        on_delete=models.CASCADE,
        related_name="items",
    )
    position = models.PositiveIntegerField(_("position"), default=0)
    description = models.CharField(_("description"), max_length=255)
    quantity = models.DecimalField(
        _("quantity"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    unit_price = money_field(_("unit price"))
    amount = money_field(_("amount"))

    class Meta:
        ordering = ["position", "id"]
        verbose_name = _("invoice line item")
        verbose_name_plural = _("invoice line items")
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="invoice_line_quantity_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.description} × {self.quantity}"

    def save(self, *args, **kwargs) -> None:
        self.amount = money(self.quantity * self.unit_price)
        super().save(*args, **kwargs)


class InvoicePayment(models.Model):
    """A payment recorded against an invoice. No gateway call is made."""

    class Method(models.TextChoices):
        BANK_TRANSFER = "bank_transfer", _("Bank transfer")
        UPI = "upi", _("UPI")
        CARD = "card", _("Card")
        CHEQUE = "cheque", _("Cheque")
        CASH = "cash", _("Cash")
        OTHER = "other", _("Other")

    invoice = models.ForeignKey(
        Invoice,
        verbose_name=_("invoice"),
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = money_field(_("amount"))
    payment_date = models.DateField(_("payment date"))
    method = models.CharField(
        _("method"), max_length=20, choices=Method.choices, default=Method.BANK_TRANSFER
    )
    reference = models.CharField(_("reference"), max_length=120, blank=True)
    note = models.CharField(_("note"), max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("recorded by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_invoice_payments",
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-id"]
        verbose_name = _("invoice payment")
        verbose_name_plural = _("invoice payments")
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="invoice_payment_amount_positive",
            ),
        ]
        indexes = [models.Index(fields=["invoice", "-payment_date"])]

    def __str__(self) -> str:
        return f"{self.invoice.invoice_number} payment {self.amount}"


class InvoiceReminder(models.Model):
    """A payment reminder that was emailed to the client."""

    class Trigger(models.TextChoices):
        MANUAL = "manual", _("Manual")
        DUE_SOON = "due_soon", _("Due soon")
        OVERDUE = "overdue", _("Overdue")

    invoice = models.ForeignKey(
        Invoice,
        verbose_name=_("invoice"),
        on_delete=models.CASCADE,
        related_name="reminders",
    )
    recipient_email = models.EmailField(_("recipient email"))
    subject = models.CharField(_("subject"), max_length=200)
    message = models.TextField(_("message"))
    trigger = models.CharField(
        _("trigger"), max_length=20, choices=Trigger.choices, default=Trigger.MANUAL
    )
    provider = models.CharField(_("provider"), max_length=20, blank=True)
    message_id = models.CharField(_("message id"), max_length=255, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("sent by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoice_reminders",
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = _("invoice reminder")
        verbose_name_plural = _("invoice reminders")
        indexes = [models.Index(fields=["invoice", "-created_at"])]

    def __str__(self) -> str:
        return f"Reminder for {self.invoice.invoice_number}"


class InvoiceAttachment(models.Model):
    """A PDF or image uploaded against an invoice.

    This is where a scanned signed copy, the original supplier document or a
    receipt is kept. The file is stored on disk; the row keeps the metadata.
    """

    class Kind(models.TextChoices):
        ORIGINAL = "original", _("Original invoice")
        SIGNED = "signed", _("Signed copy")
        RECEIPT = "receipt", _("Payment receipt")
        OTHER = "other", _("Other")

    invoice = models.ForeignKey(
        Invoice,
        verbose_name=_("invoice"),
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    kind = models.CharField(
        _("kind"), max_length=20, choices=Kind.choices, default=Kind.ORIGINAL
    )
    title = models.CharField(_("title"), max_length=200, blank=True)
    file = models.FileField(_("file"), upload_to=invoice_upload_path)
    original_name = models.CharField(_("original name"), max_length=255)
    content_type = models.CharField(_("content type"), max_length=100, blank=True)
    size = models.PositiveBigIntegerField(_("size"), default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("uploaded by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoice_attachments",
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = _("invoice attachment")
        verbose_name_plural = _("invoice attachments")
        indexes = [models.Index(fields=["invoice", "-created_at"])]

    def __str__(self) -> str:
        return self.title or self.original_name


@receiver(post_delete, sender=InvoiceAttachment)
def _delete_attachment_file(sender, instance: InvoiceAttachment, **kwargs) -> None:
    """Remove the file from storage when its row is deleted."""
    if instance.file:
        instance.file.delete(save=False)
