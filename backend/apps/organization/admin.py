"""Django admin for teams."""

from django.contrib import admin

from .models import Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "lead", "member_count"]
    search_fields = ["name", "lead__first_name", "lead__last_name"]
    raw_id_fields = ["lead"]

    @admin.display(description="Members")
    def member_count(self, obj: Team) -> int:
        return obj.members.count()
