"""Team serializers."""

from rest_framework import serializers

from .models import Team


class TeamSerializer(serializers.ModelSerializer):
    lead_name = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "name", "lead", "lead_name", "member_count"]
        extra_kwargs = {"lead": {"required": False, "allow_null": True}}

    def get_lead_name(self, obj: Team) -> str | None:
        return obj.lead.full_name if obj.lead_id else None

    def get_member_count(self, obj: Team) -> int:
        # List views annotate the count; a single fresh object falls back to a
        # count query rather than showing 0.
        annotated = getattr(obj, "member_count", None)
        return annotated if annotated is not None else obj.members.count()

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("A team name is required.")

        existing = Team.objects.filter(name__iexact=name)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("A team with this name already exists.")
        return name
