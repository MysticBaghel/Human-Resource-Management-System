"""Django admin for invoices.

Invoices are written by the API/services so totals, payments and audit rows stay
consistent. The admin is read-only for financial rows; clients can be edited
there when a developer needs to correct data.
"""

from django.contrib import admin

from .models import (
    Client,
    Invoice,
    InvoiceAttachment,
    InvoiceLineItem,
    InvoiceNumberSequence,
    InvoicePayment,
    InvoiceReminder,
)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_name", "email", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "contact_name", "email", "tax_id"]

    def has_delete_permission(self, request, obj=None) -> bool:
        # Clients with invoices are protected; deactivate instead of deleting.
        return False


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    can_delete = False
    readonly_fields = [field.name for field in InvoiceLineItem._meta.fields]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number",
        "client_name",
        "issue_date",
        "due_date",
        "total_amount",
        "balance_due",
        "status",
    ]
    list_filter = ["status", "issue_date", "due_date"]
    search_fields = ["invoice_number", "client_name", "client_email", "reference"]
    list_select_related = ["client"]
    inlines = [InvoiceLineInline]
    readonly_fields = [field.name for field in Invoice._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = ["invoice", "amount", "payment_date", "method", "recorded_by"]
    list_filter = ["method", "payment_date"]
    search_fields = ["invoice__invoice_number", "reference"]
    list_select_related = ["invoice", "recorded_by"]
    readonly_fields = [field.name for field in InvoicePayment._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(InvoiceReminder)
class InvoiceReminderAdmin(admin.ModelAdmin):
    list_display = ["invoice", "recipient_email", "trigger", "sent_by", "created_at"]
    list_filter = ["trigger", "created_at"]
    search_fields = ["invoice__invoice_number", "recipient_email", "subject"]
    list_select_related = ["invoice", "sent_by"]
    readonly_fields = [field.name for field in InvoiceReminder._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(InvoiceAttachment)
class InvoiceAttachmentAdmin(admin.ModelAdmin):
    list_display = ["invoice", "kind", "title", "original_name", "size", "created_at"]
    list_filter = ["kind", "created_at"]
    search_fields = ["invoice__invoice_number", "title", "original_name"]
    list_select_related = ["invoice", "uploaded_by"]
    readonly_fields = [field.name for field in InvoiceAttachment._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(InvoiceNumberSequence)
class InvoiceNumberSequenceAdmin(admin.ModelAdmin):
    list_display = ["year", "last_number", "updated_at"]
    readonly_fields = [field.name for field in InvoiceNumberSequence._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
