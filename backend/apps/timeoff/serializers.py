"""Serializers for leave types, balances, requests and the calendar."""

from decimal import Decimal

from rest_framework import serializers

from .models import Holiday, LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    annual_days = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        coerce_to_string=False,
        required=False,
        default=Decimal("0"),
    )
    carry_over_max = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        coerce_to_string=False,
        required=False,
        default=Decimal("0"),
    )

    class Meta:
        model = LeaveType
        fields = [
            "id",
            "name",
            "annual_days",
            "is_paid",
            "requires_approval",
            "carry_over_max",
        ]

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("A name is required.")
        return name


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    allocated = serializers.DecimalField(
        max_digits=5, decimal_places=1, coerce_to_string=False, read_only=True
    )
    used = serializers.DecimalField(
        max_digits=5, decimal_places=1, coerce_to_string=False, read_only=True
    )
    remaining = serializers.DecimalField(
        max_digits=5, decimal_places=1, coerce_to_string=False, read_only=True
    )

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "employee",
            "leave_type",
            "leave_type_name",
            "year",
            "allocated",
            "used",
            "remaining",
        ]
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    """The shape returned by every leave endpoint."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    reviewer_name = serializers.SerializerMethodField()
    days = serializers.DecimalField(
        max_digits=5, decimal_places=1, coerce_to_string=False, read_only=True
    )

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee",
            "employee_name",
            "leave_type",
            "leave_type_name",
            "start_date",
            "end_date",
            "half_day",
            "days",
            "status",
            "reviewer",
            "reviewer_name",
            "review_comment",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_reviewer_name(self, obj: LeaveRequest) -> str | None:
        return obj.reviewer.full_name if obj.reviewer_id else None


class LeaveRequestCreateSerializer(serializers.Serializer):
    """What a person may send; the employee is always the caller."""

    leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects.all())
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs: dict) -> dict:
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError(
                {"end_date": "The end date cannot be before the start date."}
            )
        return attrs


class LeaveReviewSerializer(serializers.Serializer):
    comment = serializers.CharField(
        required=False, allow_blank=True, max_length=1000
    )


class CalendarLeaveSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee",
            "employee_name",
            "leave_type",
            "leave_type_name",
            "start_date",
            "end_date",
            "half_day",
        ]
        read_only_fields = fields


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "date", "name"]
        read_only_fields = fields
