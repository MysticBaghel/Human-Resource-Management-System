"""Django admin for people.

Adding or deleting an employee is disabled on purpose: the API is the only path
that creates the login, the person record and the invite together, and people
are deactivated rather than deleted.
"""

from django.contrib import admin

from .models import Employee, EmployeeInvite


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["full_name", "job_title", "team", "employment_type", "status"]
    list_filter = ["status", "employment_type", "team"]
    search_fields = ["first_name", "last_name", "user__email", "job_title"]
    list_select_related = ["user", "team"]
    raw_id_fields = ["user", "team", "manager"]
    readonly_fields = ["status"]

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(EmployeeInvite)
class EmployeeInviteAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "expires_at", "accepted_at"]
    search_fields = ["user__email"]
    readonly_fields = ["token", "created_at", "expires_at", "accepted_at"]

    def has_add_permission(self, request) -> bool:
        return False
