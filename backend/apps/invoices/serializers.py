"""Invoice serializers: clients, invoices, payments, reminders and uploads."""

from decimal import Decimal
from pathlib import Path

from rest_framework import serializers

from .models import (
    MAX_ATTACHMENT_BYTES,
    ZERO,
    Client,
    Invoice,
    InvoiceAttachment,
    InvoiceLineItem,
    InvoicePayment,
    InvoiceReminder,
)
from .services import normalise_items

ALLOWED_ATTACHMENT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_ATTACHMENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    # Some browsers send a generic type for a valid PDF or image.
    "application/octet-stream",
}


class MoneyField(serializers.DecimalField):
    """Money as a JSON number with the project-wide precision."""

    def __init__(self, **kwargs):
        kwargs.setdefault("max_digits", 12)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("coerce_to_string", False)
        super().__init__(**kwargs)


class ClientSerializer(serializers.ModelSerializer):
    code = serializers.CharField(read_only=True)
    invoice_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            "id",
            "code",
            "name",
            "contact_name",
            "email",
            "phone",
            "billing_address",
            "tax_id",
            "notes",
            "is_active",
            "invoice_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "code", "invoice_count", "created_at", "updated_at"]

    def get_invoice_count(self, obj: Client) -> int:
        annotated = getattr(obj, "invoice_count", None)
        return annotated if annotated is not None else obj.invoices.count()

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("A client name is required.")
        existing = Client.objects.filter(name__iexact=name)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("A client with this name already exists.")
        return name

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    quantity = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    unit_price = MoneyField()
    amount = MoneyField()

    class Meta:
        model = InvoiceLineItem
        fields = ["id", "position", "description", "quantity", "unit_price", "amount"]
        read_only_fields = fields


class InvoicePaymentSerializer(serializers.ModelSerializer):
    amount = MoneyField()
    recorded_by_email = serializers.SerializerMethodField()
    method_label = serializers.CharField(source="get_method_display", read_only=True)

    class Meta:
        model = InvoicePayment
        fields = [
            "id",
            "invoice",
            "amount",
            "payment_date",
            "method",
            "method_label",
            "reference",
            "note",
            "recorded_by",
            "recorded_by_email",
            "created_at",
        ]
        read_only_fields = fields

    def get_recorded_by_email(self, obj: InvoicePayment) -> str | None:
        return obj.recorded_by.email if obj.recorded_by_id else None


class InvoiceReminderSerializer(serializers.ModelSerializer):
    sent_by_email = serializers.SerializerMethodField()
    trigger_label = serializers.CharField(source="get_trigger_display", read_only=True)

    class Meta:
        model = InvoiceReminder
        fields = [
            "id",
            "invoice",
            "recipient_email",
            "subject",
            "message",
            "trigger",
            "trigger_label",
            "provider",
            "message_id",
            "sent_by",
            "sent_by_email",
            "created_at",
        ]
        read_only_fields = fields

    def get_sent_by_email(self, obj: InvoiceReminder) -> str | None:
        return obj.sent_by.email if obj.sent_by_id else None


class InvoiceAttachmentSerializer(serializers.ModelSerializer):
    download_path = serializers.SerializerMethodField()
    uploaded_by_email = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = InvoiceAttachment
        fields = [
            "id",
            "invoice",
            "kind",
            "kind_label",
            "title",
            "original_name",
            "content_type",
            "size",
            "download_path",
            "uploaded_by",
            "uploaded_by_email",
            "created_at",
        ]
        read_only_fields = fields

    def get_download_path(self, obj: InvoiceAttachment) -> str:
        return f"/invoices/{obj.invoice_id}/attachments/{obj.pk}/download/"

    def get_uploaded_by_email(self, obj: InvoiceAttachment) -> str | None:
        return obj.uploaded_by.email if obj.uploaded_by_id else None


class InvoiceListSerializer(serializers.ModelSerializer):
    """Invoice summary used by the list, dashboard and reminder queue."""

    status_label = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)
    reminder_due = serializers.BooleanField(read_only=True)
    can_send_reminder = serializers.BooleanField(read_only=True)
    can_record_payment = serializers.BooleanField(read_only=True)
    items_count = serializers.SerializerMethodField()

    subtotal = MoneyField(read_only=True)
    discount_amount = MoneyField(read_only=True)
    tax_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True, coerce_to_string=False
    )
    tax_amount = MoneyField(read_only=True)
    total_amount = MoneyField(read_only=True)
    amount_paid = MoneyField(read_only=True)
    balance_due = MoneyField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "client",
            "client_name",
            "client_email",
            "status",
            "status_label",
            "issue_date",
            "due_date",
            "currency",
            "reference",
            "subtotal",
            "discount_amount",
            "tax_rate",
            "tax_amount",
            "total_amount",
            "amount_paid",
            "balance_due",
            "is_overdue",
            "days_overdue",
            "reminder_due",
            "can_send_reminder",
            "can_record_payment",
            "items_count",
            "reminder_count",
            "last_reminded_at",
            "sent_at",
            "sent_to",
            "sent_via",
            "sent_message_id",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_items_count(self, obj: Invoice) -> int:
        annotated = getattr(obj, "items_count", None)
        return annotated if annotated is not None else obj.items.count()


class InvoiceDetailSerializer(InvoiceListSerializer):
    """Full invoice detail, including line items and histories."""

    items = InvoiceLineItemSerializer(many=True, read_only=True)
    payments = InvoicePaymentSerializer(many=True, read_only=True)
    reminders = InvoiceReminderSerializer(many=True, read_only=True)
    attachments = InvoiceAttachmentSerializer(many=True, read_only=True)
    created_by_email = serializers.SerializerMethodField()
    can_cancel = serializers.BooleanField(read_only=True)
    is_editable = serializers.BooleanField(read_only=True)

    class Meta(InvoiceListSerializer.Meta):
        fields = [
            *InvoiceListSerializer.Meta.fields,
            "client_contact_name",
            "client_address",
            "client_tax_id",
            "notes",
            "terms",
            "cancelled_at",
            "created_by",
            "created_by_email",
            "can_cancel",
            "is_editable",
            "items",
            "payments",
            "reminders",
            "attachments",
        ]
        read_only_fields = fields

    def get_created_by_email(self, obj: Invoice) -> str | None:
        return obj.created_by.email if obj.created_by_id else None


class InvoiceLineWriteSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=255)
    quantity = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )
    unit_price = MoneyField(min_value=ZERO)

    def validate_description(self, value: str) -> str:
        description = value.strip()
        if not description:
            raise serializers.ValidationError("A description is required.")
        return description


class InvoiceWriteSerializer(serializers.Serializer):
    """Create or edit a draft invoice. Sent invoices are immutable."""

    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), required=False
    )
    issue_date = serializers.DateField(required=False)
    due_date = serializers.DateField(required=False)
    currency = serializers.RegexField(
        r"^[A-Za-z]{3}$",
        required=False,
        error_messages={"invalid": "Use a three-letter currency code."},
    )
    reference = serializers.CharField(
        required=False, allow_blank=True, max_length=100
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    terms = serializers.CharField(required=False, allow_blank=True)
    discount_amount = MoneyField(required=False, default=ZERO, min_value=ZERO)
    tax_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=ZERO,
        min_value=ZERO,
        max_value=100,
    )
    items = InvoiceLineWriteSerializer(many=True, required=False)

    def validate_currency(self, value: str) -> str:
        return value.upper()

    def validate(self, attrs: dict) -> dict:
        invoice: Invoice | None = self.context.get("invoice")

        if invoice is None:
            missing = [
                field
                for field in ("client", "issue_date", "due_date", "items")
                if field not in attrs
            ]
            if missing:
                raise serializers.ValidationError(
                    {field: ["This field is required."] for field in missing}
                )

        issue_date = attrs.get(
            "issue_date", invoice.issue_date if invoice is not None else None
        )
        due_date = attrs.get(
            "due_date", invoice.due_date if invoice is not None else None
        )
        if issue_date and due_date and due_date < issue_date:
            raise serializers.ValidationError(
                {"due_date": ["The due date must be on or after the issue date."]}
            )

        items = attrs.get("items")
        if items is not None:
            if not items:
                raise serializers.ValidationError(
                    {"items": ["An invoice needs at least one line item."]}
                )
            # Reuse the service's line validation so API and service agree on
            # quantity, price and description rules.
            try:
                lines = normalise_items(items)
            except serializers.ValidationError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise serializers.ValidationError({"items": [str(exc)]}) from exc
            subtotal = sum((line["amount"] for line in lines), ZERO)
        elif invoice is not None:
            subtotal = invoice.subtotal
        else:
            subtotal = ZERO

        discount = attrs.get(
            "discount_amount",
            invoice.discount_amount if invoice is not None else ZERO,
        )
        if discount > subtotal:
            raise serializers.ValidationError(
                {
                    "discount_amount": [
                        "The discount cannot be greater than the subtotal."
                    ]
                }
            )
        return attrs


class InvoiceSendSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField(required=False, allow_blank=True)
    subject = serializers.CharField(
        required=False, allow_blank=True, max_length=200
    )
    message = serializers.CharField(required=False, allow_blank=True, max_length=5000)


class InvoicePaymentCreateSerializer(serializers.Serializer):
    amount = MoneyField(min_value=ZERO)
    payment_date = serializers.DateField(required=False)
    method = serializers.ChoiceField(
        choices=InvoicePayment.Method.choices,
        required=False,
        default=InvoicePayment.Method.BANK_TRANSFER,
    )
    reference = serializers.CharField(
        required=False, allow_blank=True, max_length=120
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_amount(self, value):
        if value <= ZERO:
            raise serializers.ValidationError("Enter a payment amount above zero.")
        return value


class InvoiceReminderCreateSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField(required=False, allow_blank=True)
    subject = serializers.CharField(
        required=False, allow_blank=True, max_length=200
    )
    message = serializers.CharField(required=False, allow_blank=True, max_length=5000)


class InvoiceAttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    kind = serializers.ChoiceField(
        choices=InvoiceAttachment.Kind.choices,
        required=False,
        default=InvoiceAttachment.Kind.ORIGINAL,
    )
    title = serializers.CharField(required=False, allow_blank=True, max_length=200)

    def validate_file(self, value):
        name = Path(value.name or "").suffix.lower()
        if name not in ALLOWED_ATTACHMENT_EXTENSIONS:
            raise serializers.ValidationError(
                "Upload a PDF, PNG, JPG or WEBP file."
            )
        if value.size > MAX_ATTACHMENT_BYTES:
            raise serializers.ValidationError("The file must be 10 MB or smaller.")
        content_type = getattr(value, "content_type", "") or ""
        if content_type and content_type not in ALLOWED_ATTACHMENT_TYPES:
            raise serializers.ValidationError(
                "The file type does not match an allowed PDF or image."
            )
        return value
