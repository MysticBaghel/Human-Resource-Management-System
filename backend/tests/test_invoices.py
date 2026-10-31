"""Invoices: clients, generation, payments, reminders, uploads, PDFs and audit."""

import base64
from datetime import date, timedelta
from decimal import Decimal
from email import message_from_bytes
from io import StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.summary import summarize
from apps.invoices import gmail, services
from apps.invoices.models import (
    Invoice,
    InvoiceAttachment,
    InvoicePayment,
    InvoiceReminder,
)
from rest_framework.exceptions import ValidationError

INVOICES = "/api/v1/invoices/"
CLIENTS = "/api/v1/clients/"
DASHBOARD = f"{INVOICES}dashboard/"
QUEUE = f"{INVOICES}reminder-queue/"
REMINDERS = f"{INVOICES}reminders/"


def invoice_payload(client, **overrides) -> dict:
    payload = {
        "client": client.pk,
        "issue_date": "2026-01-10",
        "due_date": "2026-02-09",
        "currency": "INR",
        "reference": "PO-2026-14",
        "notes": "Thanks for your business.",
        "terms": "Payment within 30 days by bank transfer.",
        "discount_amount": "100.00",
        "tax_rate": "18.00",
        "items": [
            {
                "description": "Consulting services",
                "quantity": "2",
                "unit_price": "1000.00",
            },
            {
                "description": "Support retainer",
                "quantity": "3",
                "unit_price": "250.50",
            },
        ],
    }
    payload.update(overrides)
    return payload


def detail_url(invoice: Invoice) -> str:
    return f"{INVOICES}{invoice.pk}/"


def pay(write, invoice: Invoice, amount: str, **overrides):
    payload = {
        "amount": amount,
        "payment_date": timezone.localdate().isoformat(),
        "method": "bank_transfer",
        "reference": "UTR-9988",
        "note": "",
    }
    payload.update(overrides)
    return write("post", f"{detail_url(invoice)}payment/", payload)


def remind(write, invoice: Invoice, **overrides):
    payload = {}
    payload.update(overrides)
    return write("post", f"{detail_url(invoice)}reminder/", payload)


class TestClients:
    def test_hr_creates_a_client(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        response = api_write(
            "post",
            CLIENTS,
            {
                "name": "Acme Industries",
                "contact_name": "Priya Client",
                "email": "Billing@Acme.test",
                "billing_address": "12 Market Road\nMumbai",
                "tax_id": "27AABCU9603R1ZM",
            },
        )

        assert response.status_code == 201
        assert response.data["name"] == "Acme Industries"
        assert response.data["email"] == "billing@acme.test"
        assert response.data["code"].startswith("CLI-")
        assert response.data["is_active"] is True

    @pytest.mark.parametrize("role_attr", ["manager_user", "employee_user"])
    def test_manager_and_employee_cannot_read_or_create_clients(
        self, auth_client, api_client, api_write, demo_org, role_attr
    ):
        auth_client(getattr(demo_org, role_attr))

        assert api_client.get(CLIENTS).status_code == 403
        assert (
            api_write("post", CLIENTS, {"name": "Nope"}).status_code == 403
        )

    def test_duplicate_client_name_is_rejected(
        self, auth_client, api_write, demo_org, make_client
    ):
        make_client("Acme Industries")
        auth_client(demo_org.hr)

        response = api_write("post", CLIENTS, {"name": "acme industries"})

        assert response.status_code == 400
        assert "name" in response.data["fields"]

    def test_client_with_invoices_cannot_be_deleted(
        self, auth_client, api_delete, demo_org, make_invoice
    ):
        invoice = make_invoice()
        auth_client(demo_org.hr)

        response = api_delete(f"{CLIENTS}{invoice.client_id}/")

        assert response.status_code == 400
        assert "cannot be deleted" in response.data["detail"]

    def test_unused_client_can_be_deleted(
        self, auth_client, api_delete, demo_org, make_client
    ):
        client = make_client("Unused")
        auth_client(demo_org.hr)

        response = api_delete(f"{CLIENTS}{client.pk}/")

        assert response.status_code == 204

    def test_active_filter(self, auth_client, api_client, demo_org, make_client):
        make_client("Active Co")
        make_client("Inactive Co", is_active=False)
        auth_client(demo_org.hr)

        response = api_client.get(CLIENTS, {"active": "true"})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["name"] == "Active Co"


class TestInvoiceGeneration:
    def test_hr_generates_an_invoice_with_exact_totals(
        self, auth_client, api_write, demo_org, make_client
    ):
        client = make_client()
        auth_client(demo_org.hr)

        response = api_write("post", INVOICES, invoice_payload(client))

        assert response.status_code == 201
        data = response.data
        assert data["invoice_number"] == "INV-2026-0001"
        assert data["status"] == "draft"
        assert data["client_name"] == "Acme Industries"
        assert data["client_email"] == "billing@acme.test"
        assert data["reference"] == "PO-2026-14"
        assert Decimal(str(data["subtotal"])) == Decimal("2751.50")
        assert Decimal(str(data["discount_amount"])) == Decimal("100.00")
        rendered = response.json()
        assert rendered["tax_rate"] == 18.0
        assert isinstance(rendered["items"][0]["quantity"], (int, float))
        assert Decimal(str(data["tax_amount"])) == Decimal("477.27")
        assert Decimal(str(data["total_amount"])) == Decimal("3128.77")
        assert Decimal(str(data["balance_due"])) == Decimal("3128.77")
        assert Decimal(str(data["amount_paid"])) == Decimal("0.00")
        assert data["items_count"] == 2
        assert len(data["items"]) == 2
        assert data["items"][1]["description"] == "Support retainer"
        assert Decimal(str(data["items"][1]["amount"])) == Decimal("751.50")
        assert data["is_editable"] is True
        assert data["can_cancel"] is True

    def test_numbers_increment_and_reset_per_year(
        self, auth_client, api_write, demo_org, make_client
    ):
        client = make_client()
        auth_client(demo_org.hr)

        first = api_write("post", INVOICES, invoice_payload(client))
        second = api_write("post", INVOICES, invoice_payload(client))
        next_year = api_write(
            "post",
            INVOICES,
            invoice_payload(client, issue_date="2027-03-01", due_date="2027-03-31"),
        )

        assert first.data["invoice_number"] == "INV-2026-0001"
        assert second.data["invoice_number"] == "INV-2026-0002"
        assert next_year.data["invoice_number"] == "INV-2027-0001"

    def test_client_snapshot_is_not_rewritten_by_client_edits(
        self, auth_client, api_write, api_client, demo_org, make_client
    ):
        client = make_client()
        auth_client(demo_org.hr)
        created = api_write("post", INVOICES, invoice_payload(client))
        invoice_id = created.data["id"]

        api_write("patch", f"{CLIENTS}{client.pk}/", {"name": "Renamed Client"})
        detail = api_client.get(f"{INVOICES}{invoice_id}/")

        assert detail.status_code == 200
        assert detail.data["client_name"] == "Acme Industries"
        assert detail.data["client"] == client.pk

    @pytest.mark.parametrize("role_attr", ["manager_user", "employee_user"])
    def test_only_hr_and_admin_can_use_invoices(
        self, auth_client, api_client, api_write, demo_org, make_client, role_attr
    ):
        client = make_client()
        auth_client(getattr(demo_org, role_attr))

        assert api_client.get(INVOICES).status_code == 403
        assert api_write("post", INVOICES, invoice_payload(client)).status_code == 403

    def test_invalid_invoice_payloads_are_rejected(
        self, auth_client, api_write, demo_org, make_client
    ):
        client = make_client()
        auth_client(demo_org.hr)

        no_items = api_write(
            "post", INVOICES, invoice_payload(client, items=[])
        )
        bad_dates = api_write(
            "post",
            INVOICES,
            invoice_payload(client, due_date="2025-12-01"),
        )
        too_much_discount = api_write(
            "post", INVOICES, invoice_payload(client, discount_amount="99999.00")
        )
        bad_quantity = api_write(
            "post",
            INVOICES,
            invoice_payload(
                client,
                items=[{"description": "Zero", "quantity": "0", "unit_price": "10"}],
            ),
        )

        assert no_items.status_code == 400
        assert "items" in no_items.data["fields"]
        assert bad_dates.status_code == 400
        assert "due_date" in bad_dates.data["fields"]
        assert too_much_discount.status_code == 400
        assert "discount_amount" in too_much_discount.data["fields"]
        assert bad_quantity.status_code == 400
        assert "items" in bad_quantity.data["fields"]

    def test_inactive_client_cannot_be_invoiced(
        self, auth_client, api_write, demo_org, make_client
    ):
        client = make_client("Dormant Co", is_active=False)
        auth_client(demo_org.hr)

        response = api_write("post", INVOICES, invoice_payload(client))

        assert response.status_code == 400
        assert "client" in response.data["fields"]


class TestInvoiceLifecycle:
    def test_draft_can_be_edited_and_keeps_line_audit(
        self, auth_client, api_write, api_client, demo_org, make_client
    ):
        client = make_client()
        auth_client(demo_org.hr)
        created = api_write("post", INVOICES, invoice_payload(client))
        invoice_id = created.data["id"]

        updated = api_write(
            "patch",
            f"{INVOICES}{invoice_id}/",
            {
                "items": [
                    {
                        "description": "New scope",
                        "quantity": "1",
                        "unit_price": "5000.00",
                    }
                ],
                "discount_amount": "0.00",
            },
        )

        assert updated.status_code == 200
        assert Decimal(str(updated.data["subtotal"])) == Decimal("5000.00")
        assert Decimal(str(updated.data["tax_rate"])) == Decimal("18.00")
        assert Decimal(str(updated.data["total_amount"])) == Decimal("5900.00")
        assert len(updated.data["items"]) == 1
        assert updated.data["items"][0]["description"] == "New scope"

        detail = api_client.get(f"{INVOICES}{invoice_id}/")
        assert detail.data["items_count"] == 1

        update_log = AuditLog.objects.filter(
            model="invoices.invoice", action="update"
        ).latest("id")
        line_change = update_log.changes["changes"]["line_items"]
        assert line_change["before"][0]["description"] == "Consulting services"
        assert line_change["after"][0]["description"] == "New scope"

    def test_issue_year_cannot_change_on_a_draft(
        self, auth_client, api_write, demo_org, make_invoice
    ):
        invoice = make_invoice(status="draft", issue_date=date(2026, 1, 5))
        auth_client(demo_org.hr)

        response = api_write(
            "patch",
            detail_url(invoice),
            {"issue_date": "2027-01-05", "due_date": "2027-02-04"},
        )

        assert response.status_code == 400
        assert "issue_date" in response.data["fields"]

    def test_send_then_payment_lifecycle(
        self, auth_client, api_write, api_client, demo_org, make_invoice
    ):
        invoice = make_invoice(status="draft")
        auth_client(demo_org.hr)

        sent = api_write("post", f"{detail_url(invoice)}send/")
        assert sent.status_code == 200
        assert sent.data["status"] == "sent"
        assert sent.data["sent_at"] is not None

        duplicate = api_write("post", f"{detail_url(invoice)}send/")
        assert duplicate.status_code == 400

        locked_edit = api_write(
            "patch", detail_url(invoice), {"reference": "Nope"}
        )
        assert locked_edit.status_code == 400

        partial = pay(api_write, invoice, "500.00")
        assert partial.status_code == 201
        assert partial.data["status"] == "partially_paid"
        assert Decimal(str(partial.data["amount_paid"])) == Decimal("500.00")
        assert Decimal(str(partial.data["balance_due"])) == Decimal("1500.00")

        final = pay(api_write, invoice, "1500.00")
        assert final.status_code == 201
        assert final.data["status"] == "paid"
        assert Decimal(str(final.data["balance_due"])) == Decimal("0.00")
        assert final.data["paid_at"] is not None
        assert len(final.data["payments"]) == 2

        detail = api_client.get(detail_url(invoice))
        assert detail.data["status"] == "paid"
        assert detail.data["can_record_payment"] is False
        assert detail.data["can_cancel"] is False

        overpay = pay(api_write, invoice, "1.00")
        assert overpay.status_code == 400

    def test_payment_cannot_exceed_balance_or_apply_to_a_draft(
        self, auth_client, api_write, demo_org, make_invoice
    ):
        draft = make_invoice(status="draft")
        sent = make_invoice()
        auth_client(demo_org.hr)

        draft_payment = pay(api_write, draft, "10.00")
        overpay = pay(api_write, sent, "99999.00")

        assert draft_payment.status_code == 400
        assert overpay.status_code == 400
        assert InvoicePayment.objects.count() == 0

    def test_sent_invoice_can_be_cancelled_only_while_unpaid(
        self, auth_client, api_write, demo_org, make_invoice
    ):
        invoice = make_invoice()
        auth_client(demo_org.hr)

        cancelled = api_write("post", f"{detail_url(invoice)}cancel/")

        assert cancelled.status_code == 200
        assert cancelled.data["status"] == "cancelled"
        assert cancelled.data["cancelled_at"] is not None
        assert cancelled.data["can_cancel"] is False
        assert pay(api_write, invoice, "10.00").status_code == 400
        assert (
            api_write("post", f"{detail_url(invoice)}send/").status_code == 400
        )

    def test_invoice_delete_is_refused(
        self, auth_client, api_delete, demo_org, make_invoice
    ):
        invoice = make_invoice()
        auth_client(demo_org.hr)

        response = api_delete(detail_url(invoice))

        assert response.status_code == 405

    def test_filters_scope_the_invoice_list(
        self, auth_client, api_client, demo_org, make_invoice, make_client
    ):
        today = timezone.localdate()
        overdue = make_invoice(
            issue_date=today - timedelta(days=30),
            due_date=today - timedelta(days=5),
        )
        make_invoice(
            issue_date=today,
            due_date=today + timedelta(days=20),
            status="draft",
        )
        other_client = make_client("Other Co")
        make_invoice(
            other_client,
            issue_date=today,
            due_date=today + timedelta(days=10),
            status="cancelled",
        )
        auth_client(demo_org.hr)

        overdue_rows = api_client.get(INVOICES, {"status": "overdue"})
        draft_rows = api_client.get(INVOICES, {"status": "draft"})
        client_rows = api_client.get(INVOICES, {"client": other_client.pk})
        search_rows = api_client.get(INVOICES, {"search": other_client.name})
        balance_rows = api_client.get(INVOICES, {"has_balance": "true"})

        assert [row["id"] for row in overdue_rows.data["results"]] == [overdue.pk]
        assert draft_rows.data["count"] == 1
        assert client_rows.data["count"] == 1
        assert search_rows.data["count"] == 1
        assert balance_rows.data["count"] == 1

    def test_unknown_status_filter_is_rejected(
        self, auth_client, api_client, demo_org
    ):
        auth_client(demo_org.hr)

        response = api_client.get(INVOICES, {"status": "lost"})

        assert response.status_code == 400
        assert "status" in response.data["fields"]


class TestInvoiceSending:
    def test_send_emails_the_pdf_and_stamps_the_delivery(
        self, auth_client, api_write, mailoutbox, demo_org, make_invoice
    ):
        invoice = make_invoice(status="draft")
        auth_client(demo_org.hr)

        response = api_write("post", f"{detail_url(invoice)}send/")

        assert response.status_code == 200
        assert response.data["status"] == "sent"
        assert response.data["sent_to"] == "billing@acme.test"
        assert response.data["sent_via"] == "django"
        assert len(mailoutbox) == 1
        message = mailoutbox[0]
        assert message.to == ["billing@acme.test"]
        assert invoice.invoice_number in message.subject
        assert invoice.invoice_number in message.body
        assert len(message.attachments) == 1
        filename, content, content_type = message.attachments[0]
        assert filename == f"{invoice.invoice_number}.pdf"
        assert content.startswith(b"%PDF")
        assert content_type == "application/pdf"

        invoice.refresh_from_db()
        assert invoice.status == "sent"
        assert invoice.sent_to == "billing@acme.test"
        assert invoice.sent_via == "django"
        assert invoice.sent_at is not None

    def test_send_accepts_a_custom_recipient_and_message(
        self, auth_client, api_write, mailoutbox, demo_org, make_invoice
    ):
        invoice = make_invoice(status="draft")
        auth_client(demo_org.hr)

        response = api_write(
            "post",
            f"{detail_url(invoice)}send/",
            {
                "recipient_email": "ap@acme.test",
                "subject": "Your invoice is attached",
                "message": "Hello, the invoice is attached.",
            },
        )

        assert response.status_code == 200
        assert mailoutbox[0].to == ["ap@acme.test"]
        assert mailoutbox[0].subject == "Your invoice is attached"
        assert "the invoice is attached" in mailoutbox[0].body

    def test_send_fails_cleanly_when_email_is_not_configured(
        self, auth_client, api_write, demo_org, make_invoice
    ):
        invoice = make_invoice(status="draft")
        auth_client(demo_org.hr)

        with override_settings(INVOICE_EMAIL_FALLBACK=False):
            response = api_write("post", f"{detail_url(invoice)}send/")

        assert response.status_code == 400
        assert "Email delivery is not configured" in response.data["detail"]
        invoice.refresh_from_db()
        assert invoice.status == "draft"
        assert invoice.sent_at is None

    def test_gmail_message_contains_the_pdf_attachment(self, monkeypatch):
        captured: dict = {}

        class FakeRequest:
            def execute(self, num_retries=0):
                return {"id": "gmail-live-id"}

        class FakeMessages:
            def send(self, userId, body):
                captured["user_id"] = userId
                captured["raw"] = body["raw"]
                return FakeRequest()

        class FakeUsers:
            def messages(self):
                return FakeMessages()

        class FakeService:
            def users(self):
                return FakeUsers()

        from googleapiclient import discovery

        monkeypatch.setattr(discovery, "build", lambda *args, **kwargs: FakeService())

        with override_settings(
            GMAIL_CLIENT_ID="client-id",
            GMAIL_CLIENT_SECRET="client-secret",
            GMAIL_REFRESH_TOKEN="refresh-token",
            GMAIL_SENDER_EMAIL="sender@example.com",
            GMAIL_SENDER_NAME="HRMS Test",
        ):
            result = gmail.send_via_gmail(
                to="client@example.com",
                subject="Invoice attached",
                body="Please find the invoice attached.",
                attachments=[("INV-1.pdf", b"%PDF-1.4 test", "application/pdf")],
            )

        assert result == {"provider": "gmail", "message_id": "gmail-live-id"}
        assert captured["user_id"] == "me"
        raw = base64.urlsafe_b64decode(captured["raw"].encode("ascii"))
        message = message_from_bytes(raw)
        assert message["To"] == "client@example.com"
        assert message["Subject"] == "Invoice attached"
        assert "HRMS Test" in message["From"]
        attachments = [
            part for part in message.walk() if part.get_filename() == "INV-1.pdf"
        ]
        assert len(attachments) == 1
        assert attachments[0].get_content_type() == "application/pdf"
        assert attachments[0].get_payload(decode=True) == b"%PDF-1.4 test"

    def test_gmail_api_is_used_when_oauth_is_configured(
        self, auth_client, api_write, monkeypatch, demo_org, make_invoice
    ):
        invoice = make_invoice(status="draft")
        auth_client(demo_org.hr)
        calls: list[dict] = []

        def fake_send(**kwargs):
            calls.append(kwargs)
            return {"provider": "gmail", "message_id": "gmail-message-123"}

        monkeypatch.setattr(gmail, "send_via_gmail", fake_send)
        with override_settings(
            GMAIL_CLIENT_ID="client-id",
            GMAIL_CLIENT_SECRET="client-secret",
            GMAIL_REFRESH_TOKEN="refresh-token",
            GMAIL_SENDER_EMAIL="sender@example.com",
        ):
            response = api_write("post", f"{detail_url(invoice)}send/")

        assert response.status_code == 200
        assert response.data["sent_via"] == "gmail"
        assert response.data["sent_message_id"] == "gmail-message-123"
        assert len(calls) == 1
        assert calls[0]["to"] == "billing@acme.test"
        assert calls[0]["attachments"][0][0] == f"{invoice.invoice_number}.pdf"
        invoice.refresh_from_db()
        assert invoice.sent_via == "gmail"
        assert invoice.sent_message_id == "gmail-message-123"


class TestReminders:
    def _overdue_invoice(self, make_invoice):
        today = timezone.localdate()
        return make_invoice(
            issue_date=today - timedelta(days=30),
            due_date=today - timedelta(days=10),
        )

    def test_reminder_emails_the_client_and_records_the_send(
        self, auth_client, api_write, mailoutbox, demo_org, make_invoice
    ):
        invoice = self._overdue_invoice(make_invoice)
        auth_client(demo_org.hr)

        response = remind(api_write, invoice)

        assert response.status_code == 201
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["billing@acme.test"]
        assert invoice.invoice_number in mailoutbox[0].subject
        assert invoice.invoice_number in mailoutbox[0].body
        assert response.data["reminder"]["trigger"] == "manual"
        assert response.data["reminder"]["provider"] == "django"
        assert response.data["invoice"]["reminder_count"] == 1
        assert response.data["invoice"]["last_reminded_at"] is not None

    def test_cooldown_blocks_an_immediate_second_reminder(
        self, auth_client, api_write, demo_org, make_invoice
    ):
        invoice = self._overdue_invoice(make_invoice)
        auth_client(demo_org.hr)

        assert remind(api_write, invoice).status_code == 201
        second = remind(api_write, invoice)

        assert second.status_code == 400
        assert InvoiceReminder.objects.count() == 1

    def test_reminder_accepts_a_custom_recipient_and_message(
        self, auth_client, api_write, mailoutbox, demo_org, make_invoice
    ):
        invoice = self._overdue_invoice(make_invoice)
        auth_client(demo_org.hr)

        response = remind(
            api_write,
            invoice,
            recipient_email="accounts@acme.test",
            subject="Friendly nudge",
            message=f"Please pay invoice {invoice.invoice_number}.",
        )

        assert response.status_code == 201
        assert mailoutbox[0].to == ["accounts@acme.test"]
        assert mailoutbox[0].subject == "Friendly nudge"
        assert invoice.invoice_number in mailoutbox[0].body

    def test_paid_or_cancelled_invoices_cannot_be_reminded(
        self, auth_client, api_write, demo_org, make_invoice
    ):
        paid = make_invoice(status="paid", amount_paid="2000.00")
        cancelled = make_invoice(status="cancelled")
        auth_client(demo_org.hr)

        assert remind(api_write, paid).status_code == 400
        assert remind(api_write, cancelled).status_code == 400

    def test_invoice_without_a_billing_email_needs_a_recipient(
        self, auth_client, api_write, demo_org, make_invoice, make_client
    ):
        client = make_client("No Email Co", email="")
        invoice = self._overdue_invoice(
            lambda **kwargs: make_invoice(client=client, **kwargs)
        )
        auth_client(demo_org.hr)

        missing = remind(api_write, invoice)
        provided = remind(
            api_write, invoice, recipient_email="ap@noemail.test"
        )

        assert missing.status_code == 400
        assert provided.status_code == 201

    def test_reminder_queue_lists_due_and_overdue_invoices(
        self, auth_client, api_client, api_write, demo_org, make_invoice
    ):
        today = timezone.localdate()
        overdue = self._overdue_invoice(make_invoice)
        due_soon = make_invoice(
            issue_date=today,
            due_date=today + timedelta(days=3),
        )
        make_invoice(
            issue_date=today,
            due_date=today + timedelta(days=30),
        )
        make_invoice(status="draft", due_date=today + timedelta(days=1))
        auth_client(demo_org.hr)

        response = api_client.get(QUEUE, {"days": 7})

        assert response.status_code == 200
        assert response.data["count"] == 2
        assert {row["id"] for row in response.data["results"]} == {
            overdue.pk,
            due_soon.pk,
        }

        after_reminder = remind(api_write, due_soon)
        assert after_reminder.status_code == 201

        queue = api_client.get(QUEUE, {"days": 7})
        assert queue.data["count"] == 1

    def test_reminder_history_is_filterable(
        self, auth_client, api_client, api_write, demo_org, make_invoice
    ):
        invoice = self._overdue_invoice(make_invoice)
        auth_client(demo_org.hr)
        assert remind(api_write, invoice).status_code == 201

        response = api_client.get(REMINDERS, {"invoice": invoice.pk})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["invoice"] == invoice.pk

    def test_dashboard_reports_outstanding_and_collected_amounts(
        self, auth_client, api_client, api_write, demo_org, make_invoice
    ):
        today = timezone.localdate()
        overdue = self._overdue_invoice(make_invoice)
        make_invoice(
            issue_date=today,
            due_date=today + timedelta(days=2),
        )
        paid = make_invoice(
            issue_date=today,
            due_date=today + timedelta(days=30),
        )
        auth_client(demo_org.hr)
        assert pay(api_write, paid, "2000.00").status_code == 201

        response = api_client.get(DASHBOARD)

        assert response.status_code == 200
        assert response.data["outstanding_count"] == 2
        assert response.data["overdue_count"] == 1
        assert response.data["due_soon_count"] == 1
        assert Decimal(response.data["outstanding_amount"]) == Decimal("4000.00")
        assert Decimal(response.data["overdue_amount"]) == Decimal("2000.00")
        assert Decimal(response.data["collected_this_month"]) == Decimal("2000.00")
        assert response.data["reminder_queue_count"] == 2
        assert len(response.data["recent_invoices"]) == 3
        assert overdue.pk in {row["id"] for row in response.data["recent_invoices"]}

    def test_scheduled_command_sends_due_reminders_once(
        self, demo_org, make_invoice, mailoutbox
    ):
        today = timezone.localdate()
        make_invoice(issue_date=today, due_date=today + timedelta(days=2))
        far = make_invoice(issue_date=today, due_date=today + timedelta(days=45))

        out = StringIO()
        call_command("send_invoice_reminders", days=7, stdout=out)

        assert len(mailoutbox) == 1
        assert "Sent 1 reminder" in out.getvalue()
        assert far.invoice_number not in mailoutbox[0].body

        again = StringIO()
        call_command("send_invoice_reminders", days=7, stdout=again)
        assert len(mailoutbox) == 1
        assert "No invoices need a reminder" in again.getvalue()

    def test_scheduled_command_dry_run_sends_nothing(
        self, demo_org, make_invoice, mailoutbox
    ):
        today = timezone.localdate()
        invoice = make_invoice(issue_date=today, due_date=today + timedelta(days=2))

        out = StringIO()
        call_command("send_invoice_reminders", days=7, dry_run=True, stdout=out)

        assert len(mailoutbox) == 0
        assert invoice.invoice_number in out.getvalue()
        assert "would be reminded" in out.getvalue()

    def test_service_force_allows_an_early_resend(
        self, demo_org, make_invoice, mailoutbox
    ):
        today = timezone.localdate()
        invoice = make_invoice(issue_date=today, due_date=today + timedelta(days=2))

        services.send_invoice_reminder(invoice=invoice, actor=demo_org.hr)
        with pytest.raises(ValidationError):
            services.send_invoice_reminder(invoice=invoice, actor=demo_org.hr)
        services.send_invoice_reminder(
            invoice=invoice, actor=demo_org.hr, force=True
        )

        assert len(mailoutbox) == 2
        assert InvoiceReminder.objects.count() == 2


class TestUploads:
    def _pdf(self, name: str = "signed-invoice.pdf") -> SimpleUploadedFile:
        return SimpleUploadedFile(
            name,
            b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n",
            content_type="application/pdf",
        )

    def test_upload_list_download_and_delete_an_attachment(
        self,
        auth_client,
        api_client,
        api_upload,
        api_delete,
        media_root,
        demo_org,
        make_invoice,
    ):
        invoice = make_invoice()
        auth_client(demo_org.hr)

        upload = api_upload(
            f"{detail_url(invoice)}attachments/",
            {"file": self._pdf(), "kind": "signed", "title": "Signed copy"},
        )

        assert upload.status_code == 201
        assert upload.data["kind"] == "signed"
        assert upload.data["title"] == "Signed copy"
        assert upload.data["original_name"] == "signed-invoice.pdf"
        assert upload.data["size"] > 0
        assert upload.data["download_path"].endswith("/download/")
        attachment = InvoiceAttachment.objects.get(pk=upload.data["id"])
        assert attachment.file.storage.exists(attachment.file.name)
        assert len(list(media_root.rglob("*.pdf"))) == 1

        listed = api_client.get(f"{detail_url(invoice)}attachments/")
        assert listed.status_code == 200
        assert len(listed.data) == 1

        download = api_client.get(f"/api/v1{upload.data['download_path']}")
        assert download.status_code == 200
        assert b"".join(download.streaming_content).startswith(b"%PDF")

        deleted = api_delete(
            f"{detail_url(invoice)}attachments/{attachment.pk}/"
        )
        assert deleted.status_code == 204
        assert not InvoiceAttachment.objects.filter(pk=attachment.pk).exists()
        assert not attachment.file.storage.exists(attachment.file.name)

    def test_wrong_file_type_and_oversized_files_are_rejected(
        self,
        auth_client,
        api_upload,
        media_root,
        demo_org,
        make_invoice,
    ):
        invoice = make_invoice()
        auth_client(demo_org.hr)

        wrong_extension = api_upload(
            f"{detail_url(invoice)}attachments/",
            {
                "file": SimpleUploadedFile(
                    "malware.exe", b"MZ", content_type="application/octet-stream"
                )
            },
        )
        wrong_type = api_upload(
            f"{detail_url(invoice)}attachments/",
            {
                "file": SimpleUploadedFile(
                    "notes.pdf", b"%PDF", content_type="text/plain"
                )
            },
        )
        oversized = api_upload(
            f"{detail_url(invoice)}attachments/",
            {
                "file": SimpleUploadedFile(
                    "huge.pdf",
                    b"x" * (10 * 1024 * 1024 + 1),
                    content_type="application/pdf",
                )
            },
        )

        assert wrong_extension.status_code == 400
        assert wrong_type.status_code == 400
        assert oversized.status_code == 400
        assert InvoiceAttachment.objects.count() == 0

    @pytest.mark.parametrize("role_attr", ["manager_user", "employee_user"])
    def test_non_hr_cannot_upload(
        self, auth_client, api_upload, media_root, demo_org, make_invoice, role_attr
    ):
        invoice = make_invoice()
        auth_client(getattr(demo_org, role_attr))

        response = api_upload(
            f"{detail_url(invoice)}attachments/", {"file": self._pdf()}
        )

        assert response.status_code == 403


class TestInvoicePdf:
    def test_hr_downloads_a_pdf_invoice(
        self, auth_client, api_client, demo_org, make_invoice
    ):
        invoice = make_invoice()
        auth_client(demo_org.hr)

        response = api_client.get(f"{detail_url(invoice)}pdf/")

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")
        assert len(response.content) > 1000

    def test_pdf_download_accepts_an_application_pdf_accept_header(
        self, auth_client, api_client, demo_org, make_invoice
    ):
        invoice = make_invoice()
        auth_client(demo_org.hr)

        response = api_client.get(
            f"{detail_url(invoice)}pdf/", HTTP_ACCEPT="application/pdf"
        )

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")

    @pytest.mark.parametrize("role_attr", ["manager_user", "employee_user"])
    def test_non_hr_cannot_download_invoices(
        self, auth_client, api_client, demo_org, make_invoice, role_attr
    ):
        invoice = make_invoice()
        auth_client(getattr(demo_org, role_attr))

        assert api_client.get(f"{detail_url(invoice)}pdf/").status_code == 403


class TestInvoiceAudit:
    def test_generation_payment_and_reminder_write_audit_rows(
        self, auth_client, api_write, mailoutbox, demo_org, make_client
    ):
        client = make_client()
        auth_client(demo_org.hr)

        created = api_write("post", INVOICES, invoice_payload(client))
        invoice_id = created.data["id"]
        api_write("post", f"{INVOICES}{invoice_id}/send/")
        pay(api_write, Invoice.objects.get(pk=invoice_id), "100.00")
        remind(api_write, Invoice.objects.get(pk=invoice_id))

        invoice_logs = AuditLog.objects.filter(
            model="invoices.invoice", object_id=str(invoice_id)
        ).order_by("id")
        create_log = invoice_logs.first()
        assert create_log.action == "create"
        assert "Generated invoice" in summarize(create_log)
        assert create_log.changes["line_items"]["after"][0]["description"] == (
            "Consulting services"
        )

        statuses = [
            log.changes.get("changes", {}).get("status", {}).get("after")
            for log in invoice_logs
        ]
        assert "sent" in statuses
        assert "partially_paid" in statuses
        assert any(
            "Sent payment reminder" in summarize(log) for log in invoice_logs
        )

        assert AuditLog.objects.filter(model="invoices.invoicepayment").count() == 1
        assert AuditLog.objects.filter(model="invoices.invoicereminder").count() == 1
        assert AuditLog.objects.filter(model="invoices.client").count() >= 1

    def test_attachment_upload_is_audited(
        self,
        auth_client,
        api_upload,
        media_root,
        demo_org,
        make_invoice,
    ):
        invoice = make_invoice()
        auth_client(demo_org.hr)
        api_upload(
            f"{detail_url(invoice)}attachments/",
            {
                "file": SimpleUploadedFile(
                    "scan.pdf", b"%PDF", content_type="application/pdf"
                )
            },
        )

        log = AuditLog.objects.filter(
            model="invoices.invoiceattachment", action="create"
        ).latest("id")
        assert "Uploaded invoice attachment scan.pdf" in summarize(log)

    def test_invoice_resources_appear_in_the_audit_filter(
        self, auth_client, api_client, api_write, demo_org, make_client
    ):
        client = make_client()
        auth_client(demo_org.hr)
        api_write("post", INVOICES, invoice_payload(client))

        response = api_client.get(
            "/api/v1/audit-logs/", {"model": "invoices.invoice"}
        )

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["model_label"] == "Invoice"


class TestInvoiceServices:
    def test_totals_use_decimal_rounding(self):
        lines = services.normalise_items(
            [
                {
                    "description": "Fractional",
                    "quantity": "3",
                    "unit_price": "333.335",
                }
            ]
        )
        totals = services.calculate_totals(
            lines, Decimal("0"), Decimal("7.5"), Decimal("0")
        )

        # The unit price is normalised to two decimal places before the line
        # amount is calculated, so 333.335 becomes 333.34.
        assert totals["subtotal"] == Decimal("1000.02")
        assert totals["tax_amount"] == Decimal("75.00")
        assert totals["total_amount"] == Decimal("1075.02")

    def test_reminder_candidates_respect_the_cooldown(
        self, demo_org, make_invoice
    ):
        today = timezone.localdate()
        invoice = make_invoice(issue_date=today, due_date=today + timedelta(days=2))
        invoice.last_reminded_at = timezone.now()
        invoice.save(update_fields=["last_reminded_at"])

        assert services.reminder_candidates(days=7) == []
        assert services.reminder_candidates(days=7, cooldown_days=0) == [invoice]
