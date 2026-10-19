"""Employee serializers: read shape, write shape and invite acceptance."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User
from apps.organization.models import Team

from .models import Employee, EmployeeInvite


class EmployeeSerializer(serializers.ModelSerializer):
    """The employee shape used for reads and returned after writes."""

    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    full_name = serializers.CharField(read_only=True)
    team_name = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "email",
            "role",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "job_title",
            "team",
            "team_name",
            "manager",
            "manager_name",
            "start_date",
            "employment_type",
            "status",
        ]
        read_only_fields = fields

    def get_team_name(self, obj: Employee) -> str | None:
        return obj.team.name if obj.team_id else None

    def get_manager_name(self, obj: Employee) -> str | None:
        return obj.manager.full_name if obj.manager_id else None


class EmployeeWriteSerializer(serializers.Serializer):
    """Create or update an employee, including the fields that live on User.

    Deliberately not a ModelSerializer: email and role belong to the user row
    and are applied by ``services.update_employee`` in one transaction.
    """

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    job_title = serializers.CharField(max_length=120, required=False, allow_blank=True)
    team = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), required=False, allow_null=True
    )
    manager = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), required=False, allow_null=True
    )
    start_date = serializers.DateField()
    employment_type = serializers.ChoiceField(
        choices=Employee.EmploymentType.choices, required=False
    )

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        existing = User.objects.filter(email__iexact=email)
        employee = self.context.get("employee")
        if employee is not None:
            existing = existing.exclude(pk=employee.user_id)
        if existing.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_first_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A first name is required.")
        return value

    def validate_last_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A last name is required.")
        return value

    def validate(self, attrs: dict) -> dict:
        employee = self.context.get("employee")
        manager = attrs.get("manager")
        if employee is not None and manager is not None and manager.pk == employee.pk:
            raise serializers.ValidationError(
                {"manager": "An employee cannot be their own manager."}
            )
        return attrs


class AcceptInviteSerializer(serializers.Serializer):
    """Validate an invite token and the password the person chose."""

    token = serializers.UUIDField()
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    def validate(self, attrs: dict) -> dict:
        invite = (
            EmployeeInvite.objects.select_related("user", "user__employee")
            .filter(token=attrs["token"])
            .first()
        )
        # One message for missing, used and expired links: the endpoint should
        # not help someone guess tokens.
        if invite is None or invite.is_accepted or invite.is_expired:
            raise serializers.ValidationError(
                "This invite link is invalid or has expired."
            )

        employee = getattr(invite.user, "employee", None)
        if employee is not None and employee.status == Employee.Status.INACTIVE:
            raise serializers.ValidationError(
                "This invite link is invalid or has expired."
            )

        try:
            validate_password(attrs["password"], invite.user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc

        attrs["invite"] = invite
        return attrs
