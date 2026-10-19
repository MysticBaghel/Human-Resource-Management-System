"""Time off: leave types, yearly balances, requests and holidays.

Balances are per employee, leave type and calendar year. A request stores the
working days it costs so approving it is a pure balance movement, and the
database refuses overlapping non-cancelled requests for the same person.
"""

from decimal import Decimal

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import models
from django.db.models import F, Func, Q, Value
from django.utils.translation import gettext_lazy as _


def leave_range_expression() -> Func:
    """``daterange(start_date, end_date, '[]')``.

    Both ends are inclusive because leave dates are inclusive: a request ending
    on the 5th and one starting on the 5th do overlap. The default ``[)`` bounds
    would miss that case.
    """
    return Func(
        F("start_date"),
        F("end_date"),
        Value("[]"),
        function="daterange",
        output_field=DateRangeField(),
    )


class LeaveType(models.Model):
    """A kind of leave and its yearly allowance."""

    name = models.CharField(_("name"), max_length=80, unique=True)
    annual_days = models.DecimalField(
        _("annual days"),
        max_digits=5,
        decimal_places=1,
        default=Decimal("0"),
        help_text=_("Days allocated per employee per year."),
    )
    is_paid = models.BooleanField(_("paid"), default=True)
    requires_approval = models.BooleanField(
        _("requires approval"),
        default=True,
        help_text=_("When off, a request is approved and deducted immediately."),
    )
    carry_over_max = models.DecimalField(
        _("carry over max"),
        max_digits=5,
        decimal_places=1,
        default=Decimal("0"),
        help_text=_("Most unused days that may carry into the next year."),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("leave type")
        verbose_name_plural = _("leave types")
        constraints = [
            models.CheckConstraint(
                condition=Q(annual_days__gte=0),
                name="leavetype_annual_days_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(carry_over_max__gte=0),
                name="leavetype_carry_over_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class LeaveBalance(models.Model):
    """One employee's allowance for one leave type in one year."""

    employee = models.ForeignKey(
        "employees.Employee",
        verbose_name=_("employee"),
        on_delete=models.CASCADE,
        related_name="leave_balances",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        verbose_name=_("leave type"),
        on_delete=models.CASCADE,
        related_name="balances",
    )
    year = models.PositiveSmallIntegerField(_("year"))
    allocated = models.DecimalField(
        _("allocated"), max_digits=5, decimal_places=1, default=Decimal("0")
    )
    used = models.DecimalField(
        _("used"), max_digits=5, decimal_places=1, default=Decimal("0")
    )

    class Meta:
        ordering = ["leave_type__name", "year"]
        verbose_name = _("leave balance")
        verbose_name_plural = _("leave balances")
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "leave_type", "year"],
                name="unique_leave_balance_per_year",
            ),
            models.CheckConstraint(
                condition=Q(allocated__gte=0) & Q(used__gte=0),
                name="leave_balance_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee} · {self.leave_type} · {self.year}"

    @property
    def remaining(self):
        return self.allocated - self.used


class LeaveRequest(models.Model):
    """A request for a date range, and where it got to."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        CANCELLED = "cancelled", _("Cancelled")

    employee = models.ForeignKey(
        "employees.Employee",
        verbose_name=_("employee"),
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        verbose_name=_("leave type"),
        on_delete=models.PROTECT,
        related_name="requests",
    )
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    half_day = models.BooleanField(_("half day"), default=False)
    days = models.DecimalField(
        _("days"),
        max_digits=5,
        decimal_places=1,
        help_text=_("Working days this request costs, computed when it is made."),
    )
    status = models.CharField(
        _("status"),
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reviewer = models.ForeignKey(
        "employees.Employee",
        verbose_name=_("reviewer"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_leave_requests",
    )
    review_comment = models.TextField(_("review comment"), blank=True)
    reviewed_at = models.DateTimeField(
        _("reviewed at"),
        null=True,
        blank=True,
        help_text=_("When the request was approved or rejected."),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = _("leave request")
        verbose_name_plural = _("leave requests")
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="leave_request_end_not_before_start",
            ),
            # Postgres-only: btree_gist for the integer equality, daterange for
            # the overlap. The migration creates the extension first.
            ExclusionConstraint(
                name="leave_request_no_overlap",
                expressions=[
                    (F("employee"), RangeOperators.EQUAL),
                    (leave_range_expression(), RangeOperators.OVERLAPS),
                ],
                condition=~Q(status="cancelled"),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee} · {self.leave_type} · {self.start_date}–{self.end_date}"


class Holiday(models.Model):
    """A company holiday: never a working day."""

    date = models.DateField(_("date"), unique=True)
    name = models.CharField(_("name"), max_length=120)

    class Meta:
        ordering = ["date"]
        verbose_name = _("holiday")
        verbose_name_plural = _("holidays")

    def __str__(self) -> str:
        return f"{self.date:%d %b %Y} · {self.name}"
