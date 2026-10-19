"""Audit log serialization."""

from rest_framework import serializers

from .models import AuditLog
from .summary import action_label, model_label, summarize


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()
    actor_label = serializers.SerializerMethodField()
    action_label = serializers.SerializerMethodField()
    model_label = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "created_at",
            "actor",
            "actor_email",
            "actor_label",
            "action",
            "action_label",
            "model",
            "model_label",
            "object_id",
            "summary",
            "changes",
        ]
        read_only_fields = fields

    def get_actor_email(self, obj: AuditLog) -> str | None:
        return obj.actor.email if obj.actor_id else None

    def get_actor_label(self, obj: AuditLog) -> str:
        return obj.actor.email if obj.actor_id else "System"

    def get_action_label(self, obj: AuditLog) -> str:
        return action_label(obj.action)

    def get_model_label(self, obj: AuditLog) -> str:
        return model_label(obj.model)

    def get_summary(self, obj: AuditLog) -> str:
        return summarize(obj)
