"""The audit log is append-only: readable in the admin, never editable."""

from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "actor", "action", "model", "object_id"]
    list_filter = ["action", "model"]
    search_fields = ["object_id", "actor__email"]
    readonly_fields = ["actor", "action", "model", "object_id", "changes", "created_at"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
