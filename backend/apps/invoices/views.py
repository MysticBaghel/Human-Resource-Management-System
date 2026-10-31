"""Invoice API: clients, invoices, payments, reminders, uploads and PDFs."""

from datetime import date
from pathlib import Path

from django.conf import settings
from django.db.models import Count
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, NotFound, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.negotiation import BinaryContentNegotiation
from apps.core.permissions import IsHROrAdmin

from . import services
from .models import Client, Invoice, InvoiceAttachment, InvoiceReminder
from .pdf import render_invoice_pdf
from .serializers import (
    ClientSerializer,
    InvoiceAttachmentSerializer,
    InvoiceAttachmentUploadSerializer,
    InvoiceDetailSerializer,
    InvoiceListSerializer,
    InvoicePaymentCreateSerializer,
    InvoiceReminderCreateSerializer,
    InvoiceReminderSerializer,
    InvoiceSendSerializer,
    InvoiceWriteSerializer,
)


def _bool_param(request, name: str, default: bool = False) -> bool:
    raw = request.query_params.get(name)
    if raw is None:
        return default
    normalized = raw.lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValidationError({name: ["Use true or false."]})


def _int_param(request, name: str) -> int | None:
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ValidationError({name: ["Enter a whole number."]}) from exc


def _date_param(request, name: str) -> date | None:
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError({name: ["Use YYYY-MM-DD."]}) from exc


class ClientViewSet(viewsets.ModelViewSet):
    """Clients HR/admin bill. A client with invoices is kept, not deleted."""

    serializer_class = ClientSerializer
    permission_classes = [IsHROrAdmin]
    filter_backends = [SearchFilter]
    search_fields = ["name", "contact_name", "email", "tax_id"]

    def get_queryset(self):
        queryset = (
            Client.objects.annotate(invoice_count=Count("invoices", distinct=True))
            .order_by("name")
        )
        if "active" in self.request.query_params:
            queryset = queryset.filter(is_active=_bool_param(self.request, "active"))
        return queryset

    def destroy(self, request, *args, **kwargs):
        client = self.get_object()
        if client.invoices.exists():
            raise ValidationError(
                {
                    "detail": [
                        "This client has invoices and cannot be deleted. "
                        "Deactivate it instead."
                    ]
                }
            )
        client.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvoiceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Receivable invoices. HR/admin only.

    Invoices are never deleted: drafts can be edited, sent invoices can be
    cancelled only while unpaid, and paid invoices stay as a financial record.
    """

    permission_classes = [IsHROrAdmin]
    filter_backends = [SearchFilter]
    search_fields = [
        "invoice_number",
        "client_name",
        "client_email",
        "reference",
        "client__name",
    ]

    def _base_queryset(self):
        return (
            Invoice.objects.select_related("client", "created_by")
            .prefetch_related("items", "payments", "reminders", "attachments")
            .annotate(items_count=Count("items", distinct=True))
            .order_by("-issue_date", "-id")
        )

    def _fresh_detail(self, pk: int) -> dict:
        invoice = self._base_queryset().get(pk=pk)
        return InvoiceDetailSerializer(invoice).data

    def get_queryset(self):
        queryset = self._base_queryset()
        params = self.request.query_params
        today = timezone.localdate()

        status_value = params.get("status")
        if status_value:
            if status_value == "overdue":
                queryset = queryset.filter(
                    status__in=services.OUTSTANDING_STATUSES,
                    balance_due__gt=0,
                    due_date__lt=today,
                )
            elif status_value in Invoice.Status.values:
                queryset = queryset.filter(status=status_value)
            else:
                raise ValidationError({"status": ["Unknown invoice status."]})

        if "overdue" in params:
            overdue = _bool_param(self.request, "overdue")
            if overdue:
                queryset = queryset.filter(
                    status__in=services.OUTSTANDING_STATUSES,
                    balance_due__gt=0,
                    due_date__lt=today,
                )
            else:
                queryset = queryset.exclude(
                    status__in=services.OUTSTANDING_STATUSES,
                    balance_due__gt=0,
                    due_date__lt=today,
                )

        if "has_balance" in params:
            if _bool_param(self.request, "has_balance"):
                queryset = queryset.filter(
                    status__in=services.OUTSTANDING_STATUSES, balance_due__gt=0
                )
            else:
                queryset = queryset.filter(balance_due=0)

        client = _int_param(self.request, "client")
        if client is not None:
            queryset = queryset.filter(client_id=client)

        date_from = _date_param(self.request, "date_from")
        if date_from is not None:
            queryset = queryset.filter(issue_date__gte=date_from)
        date_to = _date_param(self.request, "date_to")
        if date_to is not None:
            queryset = queryset.filter(issue_date__lte=date_to)
        due_before = _date_param(self.request, "due_before")
        if due_before is not None:
            queryset = queryset.filter(due_date__lte=due_before)

        return queryset

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return InvoiceWriteSerializer
        if self.action == "list":
            return InvoiceListSerializer
        return InvoiceDetailSerializer

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(
            "DELETE",
            detail=(
                "Invoices are financial records and cannot be deleted. "
                "Cancel instead."
            ),
        )

    def create(self, request, *args, **kwargs):
        serializer = InvoiceWriteSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        invoice = services.create_invoice(
            actor=request.user, data=dict(serializer.validated_data)
        )
        return Response(self._fresh_detail(invoice.pk), status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        invoice = self.get_object()
        serializer = InvoiceWriteSerializer(
            data=request.data,
            partial=partial,
            context={**self.get_serializer_context(), "invoice": invoice},
        )
        serializer.is_valid(raise_exception=True)
        updated = services.update_invoice(
            invoice=invoice, data=dict(serializer.validated_data)
        )
        return Response(self._fresh_detail(updated.pk))

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Email a draft invoice with its PDF, then mark it as sent."""
        invoice = self.get_object()
        payload = InvoiceSendSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        invoice = services.send_invoice(
            invoice=invoice,
            actor=request.user,
            **payload.validated_data,
        )
        return Response(self._fresh_detail(invoice.pk))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a draft or sent invoice that has no payments."""
        invoice = services.cancel_invoice(invoice=self.get_object())
        return Response(self._fresh_detail(invoice.pk))

    @action(detail=True, methods=["post"])
    def payment(self, request, pk=None):
        """Record a full or partial payment against a sent invoice."""
        invoice = self.get_object()
        payload = InvoicePaymentCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        invoice, _payment = services.record_payment(
            invoice=invoice,
            amount=data["amount"],
            payment_date=data.get("payment_date") or timezone.localdate(),
            method=data["method"],
            reference=data.get("reference", ""),
            note=data.get("note", ""),
            actor=request.user,
        )
        return Response(self._fresh_detail(invoice.pk), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reminder(self, request, pk=None):
        """Email an outstanding invoice's client and record the reminder."""
        invoice = self.get_object()
        payload = InvoiceReminderCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        reminder = services.send_invoice_reminder(
            invoice=invoice,
            actor=request.user,
            recipient_email=data.get("recipient_email", ""),
            subject=data.get("subject", ""),
            message=data.get("message", ""),
        )
        return Response(
            {
                "reminder": InvoiceReminderSerializer(reminder).data,
                "invoice": self._fresh_detail(invoice.pk),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="pdf",
        content_negotiation_class=BinaryContentNegotiation,
    )
    def pdf(self, request, pk=None):
        """Download a generated PDF for this invoice."""
        invoice = self.get_object()
        pdf = render_invoice_pdf(invoice)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{invoice.invoice_number}.pdf"'
        )
        response["Content-Length"] = str(len(pdf))
        return response

    @action(
        detail=True,
        methods=["get", "post"],
        parser_classes=[MultiPartParser, FormParser],
        url_path="attachments",
    )
    def attachments(self, request, pk=None):
        """List or upload invoice files (original, signed copy, receipt)."""
        invoice = self.get_object()

        if request.method == "GET":
            attachments = invoice.attachments.select_related("uploaded_by").all()
            return Response(
                InvoiceAttachmentSerializer(attachments, many=True).data
            )

        serializer = InvoiceAttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded = serializer.validated_data["file"]
        attachment = InvoiceAttachment.objects.create(
            invoice=invoice,
            kind=serializer.validated_data.get(
                "kind", InvoiceAttachment.Kind.ORIGINAL
            ),
            title=serializer.validated_data.get("title", "").strip(),
            file=uploaded,
            original_name=Path(uploaded.name).name[:255],
            content_type=getattr(uploaded, "content_type", "") or "",
            size=uploaded.size,
            uploaded_by=request.user,
        )
        return Response(
            InvoiceAttachmentSerializer(attachment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path=r"attachments/(?P<attachment_id>[0-9]+)/download",
        content_negotiation_class=BinaryContentNegotiation,
    )
    def download_attachment(self, request, pk=None, attachment_id=None):
        invoice = self.get_object()
        attachment = get_object_or_404(invoice.attachments, pk=attachment_id)
        try:
            stream = attachment.file.open("rb")
        except FileNotFoundError as exc:
            raise NotFound(
                "The uploaded file is no longer available in storage."
            ) from exc
        return FileResponse(
            stream,
            as_attachment=True,
            filename=attachment.original_name,
            content_type=attachment.content_type or "application/octet-stream",
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"attachments/(?P<attachment_id>[0-9]+)",
    )
    def remove_attachment(self, request, pk=None, attachment_id=None):
        invoice = self.get_object()
        attachment = get_object_or_404(invoice.attachments, pk=attachment_id)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvoiceDashboardView(APIView):
    """Receivable metrics and recent invoices for HR/admin."""

    permission_classes = [IsHROrAdmin]

    def get(self, request) -> Response:
        data = services.build_invoice_dashboard()
        data["recent_invoices"] = InvoiceListSerializer(
            data.pop("recent_invoices"), many=True
        ).data
        return Response(data)


class InvoiceReminderQueueView(APIView):
    """Invoices due soon or overdue that are ready for a reminder."""

    permission_classes = [IsHROrAdmin]

    def get(self, request) -> Response:
        days = _int_param(request, "days")
        if days is None:
            days = services.REMINDER_HORIZON_DAYS
        if not 0 <= days <= 90:
            raise ValidationError({"days": ["Choose between 0 and 90 days."]})

        cooldown = _int_param(request, "cooldown_days")
        if cooldown is not None and not 0 <= cooldown <= 90:
            raise ValidationError(
                {"cooldown_days": ["Choose between 0 and 90 days."]}
            )

        candidates = services.reminder_candidates(
            days=days, cooldown_days=cooldown
        )
        return Response(
            {
                "as_of": timezone.localdate().isoformat(),
                "days": days,
                "cooldown_days": (
                    cooldown
                    if cooldown is not None
                    else int(
                        getattr(settings, "INVOICE_REMINDER_COOLDOWN_DAYS", 3)
                    )
                ),
                "count": len(candidates),
                "results": InvoiceListSerializer(candidates, many=True).data,
            }
        )


class InvoiceReminderListView(generics.ListAPIView):
    """Company-wide reminder history, filterable by invoice."""

    permission_classes = [IsHROrAdmin]
    serializer_class = InvoiceReminderSerializer
    filter_backends = [SearchFilter]
    search_fields = ["subject", "recipient_email", "invoice__invoice_number"]

    def get_queryset(self):
        queryset = InvoiceReminder.objects.select_related(
            "invoice", "sent_by"
        ).order_by("-created_at", "-id")
        invoice = _int_param(self.request, "invoice")
        if invoice is not None:
            queryset = queryset.filter(invoice_id=invoice)
        trigger = self.request.query_params.get("trigger")
        if trigger:
            if trigger not in InvoiceReminder.Trigger.values:
                raise ValidationError({"trigger": ["Unknown reminder trigger."]})
            queryset = queryset.filter(trigger=trigger)
        return queryset
