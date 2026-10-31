"""Serializers for salary structures, revisions and payroll records."""

from rest_framework import serializers

from apps.employees.models import Employee

from .models import (
    DEDUCTION_FIELDS,
    EARNING_FIELDS,
    MONEY_DECIMAL_PLACES,
    MONEY_MAX_DIGITS,
    ZERO,
    PayrollRecord,
    SalaryRevision,
    SalaryStructure,
)
from .services import parse_period, structure_totals


class MoneyField(serializers.DecimalField):
    """Money as a JSON number, with the payroll precision by default."""

    def __init__(self, **kwargs):
        kwargs.setdefault("max_digits", MONEY_MAX_DIGITS)
        kwargs.setdefault("decimal_places", MONEY_DECIMAL_PLACES)
        kwargs.setdefault("coerce_to_string", False)
        super().__init__(**kwargs)


class SalaryStructureSerializer(serializers.ModelSerializer):
    """Read shape for a salary structure, including calculated totals."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.SerializerMethodField()
    email = serializers.EmailField(source="employee.user.email", read_only=True)
    designation = serializers.CharField(source="employee.job_title", read_only=True)
    department = serializers.SerializerMethodField()
    date_of_joining = serializers.DateField(
        source="employee.start_date", read_only=True
    )
    created_by_email = serializers.SerializerMethodField()

    basic_salary = MoneyField(read_only=True)
    hra = MoneyField(read_only=True)
    conveyance_allowance = MoneyField(read_only=True)
    medical_allowance = MoneyField(read_only=True)
    special_allowance = MoneyField(read_only=True)
    other_allowances = MoneyField(read_only=True)
    provident_fund = MoneyField(read_only=True)
    professional_tax = MoneyField(read_only=True)
    income_tax = MoneyField(read_only=True)
    other_deductions = MoneyField(read_only=True)
    gross_salary = MoneyField(read_only=True)
    total_deductions = MoneyField(read_only=True)
    net_salary = MoneyField(read_only=True)

    class Meta:
        model = SalaryStructure
        fields = [
            "id",
            "employee",
            "employee_name",
            "employee_code",
            "email",
            "designation",
            "department",
            "date_of_joining",
            "basic_salary",
            "hra",
            "conveyance_allowance",
            "medical_allowance",
            "special_allowance",
            "other_allowances",
            "provident_fund",
            "professional_tax",
            "income_tax",
            "other_deductions",
            "gross_salary",
            "total_deductions",
            "net_salary",
            "effective_date",
            "is_active",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_employee_code(self, obj: SalaryStructure) -> str:
        return obj.employee_code

    def get_department(self, obj: SalaryStructure) -> str | None:
        employee = obj.employee
        return employee.team.name if employee.team_id else None

    def get_created_by_email(self, obj: SalaryStructure) -> str | None:
        return obj.created_by.email if obj.created_by_id else None


class SalaryStructureWriteSerializer(serializers.Serializer):
    """Create or revise a salary structure.

    ``reason`` is not stored on the structure: it belongs to the revision row
    that the service creates.
    """

    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    basic_salary = MoneyField(required=False, default=ZERO, min_value=ZERO)
    hra = MoneyField(required=False, default=ZERO, min_value=ZERO)
    conveyance_allowance = MoneyField(required=False, default=ZERO, min_value=ZERO)
    medical_allowance = MoneyField(required=False, default=ZERO, min_value=ZERO)
    special_allowance = MoneyField(required=False, default=ZERO, min_value=ZERO)
    other_allowances = MoneyField(required=False, default=ZERO, min_value=ZERO)
    provident_fund = MoneyField(required=False, default=ZERO, min_value=ZERO)
    professional_tax = MoneyField(required=False, default=ZERO, min_value=ZERO)
    income_tax = MoneyField(required=False, default=ZERO, min_value=ZERO)
    other_deductions = MoneyField(required=False, default=ZERO, min_value=ZERO)
    effective_date = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs: dict) -> dict:
        structure: SalaryStructure | None = self.context.get("structure")
        employee = attrs.get("employee")
        effective_date = attrs.get("effective_date")

        if structure is not None:
            if employee is not None and employee.pk != structure.employee_id:
                raise serializers.ValidationError(
                    {"employee": ["A salary structure cannot change employee."]}
                )
            if effective_date is not None and effective_date < structure.effective_date:
                raise serializers.ValidationError(
                    {
                        "effective_date": [
                            "A revision cannot take effect "
                            "before the current structure."
                        ]
                    }
                )

        values = {}
        for name in (*EARNING_FIELDS, *DEDUCTION_FIELDS):
            if name in attrs:
                values[name] = attrs[name]
            elif structure is not None:
                values[name] = getattr(structure, name)
            else:
                values[name] = ZERO
        totals = structure_totals(values)
        if totals["net_salary"] < 0:
            raise serializers.ValidationError(
                {
                    "other_deductions": [
                        "Total deductions cannot be greater than gross salary."
                    ]
                }
            )
        return attrs


class SalaryRevisionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    updated_by_email = serializers.SerializerMethodField()

    class Meta:
        model = SalaryRevision
        fields = [
            "id",
            "employee",
            "employee_name",
            "previous_structure",
            "new_structure",
            "previous_values",
            "new_values",
            "effective_date",
            "updated_by",
            "updated_by_email",
            "reason",
            "created_at",
        ]
        read_only_fields = fields

    def get_updated_by_email(self, obj: SalaryRevision) -> str | None:
        return obj.updated_by.email if obj.updated_by_id else None


class PayrollRecordSerializer(serializers.ModelSerializer):
    """A payroll record, including every snapshot value used by the payslip."""

    pay_period = serializers.CharField(source="pay_period_label", read_only=True)
    adjusted_gross = MoneyField(read_only=True)
    generated_by_email = serializers.SerializerMethodField()
    finalized_by_email = serializers.SerializerMethodField()

    basic_salary = MoneyField(read_only=True)
    hra = MoneyField(read_only=True)
    conveyance_allowance = MoneyField(read_only=True)
    medical_allowance = MoneyField(read_only=True)
    special_allowance = MoneyField(read_only=True)
    other_allowances = MoneyField(read_only=True)
    provident_fund = MoneyField(read_only=True)
    professional_tax = MoneyField(read_only=True)
    income_tax = MoneyField(read_only=True)
    other_deductions = MoneyField(read_only=True)
    gross_salary = MoneyField(read_only=True)
    total_deductions = MoneyField(read_only=True)
    adjustment_amount = MoneyField(read_only=True)
    net_salary = MoneyField(read_only=True)

    class Meta:
        model = PayrollRecord
        fields = [
            "id",
            "employee",
            "employee_name",
            "employee_code",
            "designation",
            "department",
            "date_of_joining",
            "payroll_month",
            "payroll_year",
            "pay_period",
            "payslip_number",
            "basic_salary",
            "hra",
            "conveyance_allowance",
            "medical_allowance",
            "special_allowance",
            "other_allowances",
            "provident_fund",
            "professional_tax",
            "income_tax",
            "other_deductions",
            "gross_salary",
            "total_deductions",
            "adjustment_amount",
            "adjustment_note",
            "adjusted_gross",
            "net_salary",
            "status",
            "payment_status",
            "payment_date",
            "payment_reference",
            "generated_by",
            "generated_by_email",
            "finalized_by",
            "finalized_by_email",
            "finalized_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_generated_by_email(self, obj: PayrollRecord) -> str | None:
        return obj.generated_by.email if obj.generated_by_id else None

    def get_finalized_by_email(self, obj: PayrollRecord) -> str | None:
        return obj.finalized_by.email if obj.finalized_by_id else None


class PayrollGenerateSerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), required=False, allow_null=True
    )

    def validate(self, attrs: dict) -> dict:
        parse_period(attrs["month"], attrs["year"])
        return attrs


class PayrollPeriodSerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2000, max_value=2100)

    def validate(self, attrs: dict) -> dict:
        parse_period(attrs["month"], attrs["year"])
        return attrs


class PayrollAdjustmentSerializer(serializers.Serializer):
    adjustment_amount = MoneyField(required=False)
    adjustment_note = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )

    def validate(self, attrs: dict) -> dict:
        if not attrs:
            raise serializers.ValidationError("Provide an adjustment amount or note.")
        return attrs


class PayrollPaymentSerializer(serializers.Serializer):
    payment_status = serializers.ChoiceField(
        choices=PayrollRecord.PaymentStatus.choices
    )
    payment_date = serializers.DateField(required=False, allow_null=True)
    payment_reference = serializers.CharField(
        required=False, allow_blank=True, max_length=120
    )

    def validate(self, attrs: dict) -> dict:
        if (
            attrs["payment_status"] == PayrollRecord.PaymentStatus.PAID
            and attrs.get("payment_date") is None
        ):
            raise serializers.ValidationError(
                {"payment_date": ["A paid payroll needs a payment date."]}
            )
        return attrs
