"""Django admin for payroll.

Payroll rows are written by the services so snapshots stay consistent and
audited. The admin is read-only; salary structures are managed in the HR
payroll screens.
"""

from django.contrib import admin

from .models import PayrollRecord, SalaryRevision, SalaryStructure


@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "effective_date",
        "is_active",
        "gross_salary",
        "total_deductions",
        "net_salary",
    ]
    list_filter = ["is_active", "effective_date"]
    search_fields = ["employee__first_name", "employee__last_name"]
    list_select_related = ["employee"]
    readonly_fields = [field.name for field in SalaryStructure._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(SalaryRevision)
class SalaryRevisionAdmin(admin.ModelAdmin):
    list_display = ["employee", "effective_date", "updated_by", "created_at"]
    list_filter = ["effective_date"]
    search_fields = ["employee__first_name", "employee__last_name"]
    list_select_related = ["employee", "updated_by"]
    readonly_fields = [field.name for field in SalaryRevision._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = [
        "employee_name",
        "payroll_year",
        "payroll_month",
        "net_salary",
        "status",
        "payment_status",
    ]
    list_filter = ["status", "payment_status", "payroll_year", "payroll_month"]
    search_fields = ["employee_name", "employee_code", "payslip_number"]
    readonly_fields = [field.name for field in PayrollRecord._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
