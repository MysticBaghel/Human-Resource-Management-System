"""Django admin for time off.

Requests and balances are read-only here: they must move through the services so
balances stay consistent and every change is audited.
"""

from django.contrib import admin

from .models import Holiday, LeaveBalance, LeaveRequest, LeaveType


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "annual_days", "is_paid", "requires_approval", "carry_over_max"]
    search_fields = ["name"]


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ["date", "name"]
    search_fields = ["name"]
    date_hierarchy = "date"


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "year", "allocated", "used"]
    list_filter = ["year", "leave_type"]
    search_fields = ["employee__first_name", "employee__last_name"]
    readonly_fields = ["employee", "leave_type", "year", "allocated", "used"]

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "start_date", "end_date", "days", "status"]
    list_filter = ["status", "leave_type"]
    search_fields = ["employee__first_name", "employee__last_name"]
    readonly_fields = [
        "employee",
        "leave_type",
        "start_date",
        "end_date",
        "half_day",
        "days",
        "status",
        "reviewer",
        "review_comment",
        "created_at",
    ]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
