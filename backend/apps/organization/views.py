"""Team endpoints."""

from django.db.models import Count
from rest_framework import viewsets
from rest_framework.filters import SearchFilter

from apps.core.permissions import TeamPermission
from apps.core.scoping import scope_teams

from .models import Team
from .serializers import TeamSerializer


class TeamViewSet(viewsets.ModelViewSet):
    """Teams: HR/admin write, managers read the teams they lead."""

    serializer_class = TeamSerializer
    permission_classes = [TeamPermission]
    filter_backends = [SearchFilter]
    search_fields = ["name", "lead__first_name", "lead__last_name"]

    def get_queryset(self):
        queryset = (
            Team.objects.select_related("lead")
            .annotate(member_count=Count("members", distinct=True))
            .order_by("name")
        )
        return scope_teams(queryset, self.request.user)
