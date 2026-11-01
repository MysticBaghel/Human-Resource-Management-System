"""Payroll models: salary structures, revisions and monthly payroll records.

Money is always a ``Decimal`` in this app. A payroll record copies every salary
component from the salary structure that applied when it was generated, so a
later revision can never rewrite an existing pay run.
"""

import calendar
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

MONEY_MAX_DIGITS = 12
MONEY_DECIMAL_PLACES = 2
ZERO = Decimal("0.00")

# The components that make up a salary. Payroll snapshots and the PDF payslip
# both use these tuples so there is one definition of a salary.
EARNING_FIELDS = (
    "basic_salary",
    "hra",
    "conveyance_allowance",
    "medical_allowance",
    "special_allowance",
    "other_allowances",
)
DEDUCTION_FIELDS = (
    "provident_fund",
    "professional_tax",
    "income_tax",
    "other_deductions",
)


def money_field(label: str, **kwargs) -> models.DecimalField:
    """A non-negative monetary column with the project-wide precision."""
    return models.DecimalField(
        label,
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=ZERO,
        validators=[MinValueValidator(ZERO)],
        **kwargs,
    )


def total_for(instance, fields: tuple[str, ...]) -> Decimal:
    """Sum Decimal components without ever touching float arithmetic."""
    return sum((getattr(instance, name) for name in fields), ZERO)


class SalaryStructure(models.Model):
    """One version of an employee's salary.

    The employee's current structure is the active row. A revision deactivates
    that row and creates a new active version, so old versions remain available
    for history and for payroll periods that predate the revision.
    """

    employee = models.ForeignKey(
        "employees.Employee",
        verbose_name=_("employee"),
        on_delete=models.CASCADE,
        related_name="salary_structures",
    )
    basic_salary = money_field(_("basic salary"))
    hra = money_field(_("house rent allowance"))
    conveyance_allowance = money_field(_("conveyance allowance"))
    medical_allowance = money_field(_("medical allowance"))
    special_allowance = money_field(_("special allowance"))
    other_allowances = money_field(_("other allowances"))

    provident_fund = money_field(_("provident fund"))
    professional_tax = money_field(_("professional tax"))
    income_tax = money_field(_("income tax / TDS"))
    other_deductions = money_field(_("other deductions"))

    effective_date = models.DateField(
        _("effective date"),
        help_text=_("The date this version starts applying."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("The employee's current structure. History rows are inactive."),
    )
    revoked_at = models.DateField(
        _("revoked at"),
        null=True,
        blank=True,
        help_text=_(
            "Set when HR revokes the structure. The row is kept for history, "
            "but payroll periods after this date cannot use it."
        ),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("created by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_salary_structures",
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ["employee__first_name", "employee__last_name", "-effective_date"]
        verbose_name = _("salary structure")
        verbose_name_plural = _("salary structures")
        constraints = [
            models.UniqueConstraint(
                fields=["employee"],
                condition=Q(is_active=True),
                name="unique_active_salary_structure_per_employee",
            ),
            models.CheckConstraint(
                condition=(
                    Q(basic_salary__gte=0)
                    & Q(hra__gte=0)
                    & Q(conveyance_allowance__gte=0)
                    & Q(medical_allowance__gte=0)
                    & Q(special_allowance__gte=0)
                    & Q(other_allowances__gte=0)
                    & Q(provident_fund__gte=0)
                    & Q(professional_tax__gte=0)
                    & Q(income_tax__gte=0)
                    & Q(other_deductions__gte=0)
                ),
                name="salary_structure_components_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["employee", "effective_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} · effective {self.effective_date}"

    @property
    def gross_salary(self) -> Decimal:
        return total_for(self, EARNING_FIELDS)

    @property
    def total_deductions(self) -> Decimal:
        return total_for(self, DEDUCTION_FIELDS)

    @property
    def net_salary(self) -> Decimal:
        return self.gross_salary - self.total_deductions

    @property
    def employee_code(self) -> str:
        return employee_code(self.employee_id)


class SalaryRevision(models.Model):
    """The before/after record of one salary structure revision."""

    employee = models.ForeignKey(
        "employees.Employee",
        verbose_name=_("employee"),
        on_delete=models.CASCADE,
        related_name="salary_revisions",
    )
    previous_structure = models.ForeignKey(
        SalaryStructure,
        verbose_name=_("previous structure"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="revisions_from",
    )
    new_structure = models.ForeignKey(
        SalaryStructure,
        verbose_name=_("new structure"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="revisions_to",
    )
    previous_values = models.JSONField(_("previous values"), default=dict)
    new_values = models.JSONField(_("new values"), default=dict)
    effective_date = models.DateField(_("effective date"))
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("updated by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="salary_revisions",
    )
    reason = models.CharField(_("reason"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = _("salary revision")
        verbose_name_plural = _("salary revisions")
        indexes = [
            models.Index(fields=["employee", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Revision for {self.employee} effective {self.effective_date}"


class PayrollRecord(models.Model):
    """One employee's pay for one month, with every value snapshotted.

    Components are copied at generation time. Changing a salary structure later
    only affects future payroll records; the values here stay fixed.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        FINALIZED = "finalized", _("Finalized")

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        PAID = "paid", _("Paid")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")

    employee = models.ForeignKey(
        "employees.Employee",
        verbose_name=_("employee"),
        on_delete=models.PROTECT,
        related_name="payroll_records",
    )
    salary_structure = models.ForeignKey(
        SalaryStructure,
        verbose_name=_("source salary structure"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payroll_records",
        help_text=_("The structure version this payroll record was copied from."),
    )

    payroll_month = models.PositiveSmallIntegerField(
        _("payroll month"),
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    payroll_year = models.PositiveSmallIntegerField(_("payroll year"))
    payslip_number = models.CharField(_("payslip number"), max_length=32, unique=True)

    # Employee details are snapshotted too: a later promotion or team move must
    # not rewrite an old payslip.
    employee_name = models.CharField(_("employee name"), max_length=200)
    employee_code = models.CharField(_("employee code"), max_length=32)
    designation = models.CharField(_("designation"), max_length=120, blank=True)
    department = models.CharField(_("department"), max_length=120, blank=True)
    date_of_joining = models.DateField(_("date of joining"))

    basic_salary = money_field(_("basic salary"))
    hra = money_field(_("house rent allowance"))
    conveyance_allowance = money_field(_("conveyance allowance"))
    medical_allowance = money_field(_("medical allowance"))
    special_allowance = money_field(_("special allowance"))
    other_allowances = money_field(_("other allowances"))

    provident_fund = money_field(_("provident fund"))
    professional_tax = money_field(_("professional tax"))
    income_tax = money_field(_("income tax / TDS"))
    other_deductions = money_field(_("other deductions"))

    gross_salary = money_field(_("gross salary"))
    total_deductions = money_field(_("total deductions"))
    adjustment_amount = models.DecimalField(
        _("adjustment amount"),
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=ZERO,
        help_text=_("Positive adds to pay, negative deducts. Applied before net pay."),
    )
    adjustment_note = models.CharField(_("adjustment note"), max_length=255, blank=True)
    net_salary = money_field(_("net salary"))

    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    payment_status = models.CharField(
        _("payment status"),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    payment_date = models.DateField(_("payment date"), null=True, blank=True)
    payment_reference = models.CharField(
        _("payment reference"), max_length=120, blank=True
    )

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("generated by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_payroll_records",
    )
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("finalized by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="finalized_payroll_records",
    )
    finalized_at = models.DateTimeField(_("finalized at"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = [
            "-payroll_year",
            "-payroll_month",
            "employee__first_name",
            "employee__last_name",
        ]
        verbose_name = _("payroll record")
        verbose_name_plural = _("payroll records")
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "payroll_year", "payroll_month"],
                name="unique_payroll_per_employee_period",
            ),
            models.CheckConstraint(
                condition=Q(payroll_month__gte=1) & Q(payroll_month__lte=12),
                name="payroll_month_valid",
            ),
            models.CheckConstraint(
                condition=Q(payroll_year__gte=2000),
                name="payroll_year_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(basic_salary__gte=0)
                    & Q(hra__gte=0)
                    & Q(conveyance_allowance__gte=0)
                    & Q(medical_allowance__gte=0)
                    & Q(special_allowance__gte=0)
                    & Q(other_allowances__gte=0)
                    & Q(provident_fund__gte=0)
                    & Q(professional_tax__gte=0)
                    & Q(income_tax__gte=0)
                    & Q(other_deductions__gte=0)
                    & Q(gross_salary__gte=0)
                    & Q(total_deductions__gte=0)
                    & Q(net_salary__gte=0)
                ),
                name="payroll_amounts_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["payroll_year", "payroll_month"]),
            models.Index(fields=["status", "payment_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee_name} · {self.pay_period_label}"

    @property
    def pay_period_label(self) -> str:
        month_name = calendar.month_name[self.payroll_month]
        return f"{month_name} {self.payroll_year}"

    @property
    def adjusted_gross(self) -> Decimal:
        return self.gross_salary + self.adjustment_amount

    def recalculate(self) -> None:
        """Recompute snapshotted totals from the current component values."""
        self.gross_salary = total_for(self, EARNING_FIELDS)
        self.total_deductions = total_for(self, DEDUCTION_FIELDS)
        self.net_salary = (
            self.gross_salary + self.adjustment_amount - self.total_deductions
        )


def employee_code(employee_id: int | None) -> str:
    """A stable display id for an employee, independent of their salary data."""
    if employee_id is None:
        return "EMP-0000"
    return f"EMP-{employee_id:04d}"
