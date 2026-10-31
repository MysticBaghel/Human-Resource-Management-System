"""Django admin for teams and the company profile."""

from django.contrib import admin

from .models import CompanyProfile, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "lead", "member_count"]
    search_fields = ["name", "lead__first_name", "lead__last_name"]
    raw_id_fields = ["lead"]

    @admin.display(description="Members")
    def member_count(self, obj: Team) -> int:
        return obj.members.count()


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    """The company name and logo used on payslips."""

    list_display = ["name", "email", "phone", "updated_at"]
    fields = ["name", "logo", "address", "email", "phone", "website"]

    def has_add_permission(self, request) -> bool:
        return not CompanyProfile.objects.exists()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
