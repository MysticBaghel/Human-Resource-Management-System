"""Audit log API: read-only, HR and admin only."""

from datetime import date

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from apps.core.permissions import IsHROrAdmin

from .models import AuditLog
from .serializers import AuditLogSerializer
from .summary import MODEL_LABELS


def _parse_date(params, name: str) -> date | None:
    raw = params.get(name)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError({name: ["Use YYYY-MM-DD."]}) from exc


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """The company audit trail.

    Read-only by design: ordinary users can never edit or delete a row, and only
    HR and admin can see the company-wide feed. Managers and employees are
    stopped here, independently of the React navigation.
    """

    serializer_class = AuditLogSerializer
    permission_classes = [IsHROrAdmin]
    filter_backends = [SearchFilter]
    search_fields = ["object_id", "actor__email", "model"]

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("actor").order_by(
            "-created_at", "-id"
        )
        params = self.request.query_params

        action_value = params.get("action")
        if action_value:
            if action_value not in AuditLog.Action.values:
                raise ValidationError({"action": ["Unknown audit action."]})
            queryset = queryset.filter(action=action_value)

        model_value = params.get("model")
        if model_value:
            if model_value not in MODEL_LABELS:
                raise ValidationError({"model": ["Unknown resource."]})
            queryset = queryset.filter(model=model_value)

        actor = params.get("actor")
        if actor:
            try:
                actor_id = int(actor)
            except ValueError as exc:
                raise ValidationError({"actor": ["Enter a whole user id."]}) from exc
            queryset = queryset.filter(actor_id=actor_id)

        date_from = _parse_date(params, "date_from")
        date_to = _parse_date(params, "date_to")
        if date_from and date_to and date_from > date_to:
            raise ValidationError(
                {"date_to": ["Must be on or after date_from."]}
            )
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset

    @action(detail=False, methods=["get"])
    def actors(self, request):
        """Distinct actors that actually appear in the log, for the filter."""
        rows = (
            AuditLog.objects.exclude(actor=None)
            .values("actor_id", "actor__email")
            .distinct()
            .order_by("actor__email")
        )
        return Response(
            [
                {"id": row["actor_id"], "email": row["actor__email"]}
                for row in rows
            ]
        )
