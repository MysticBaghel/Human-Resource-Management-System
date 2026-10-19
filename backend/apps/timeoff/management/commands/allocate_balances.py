"""Allocate a year's leave balances to every active employee."""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.employees.models import Employee
from apps.timeoff.models import LeaveBalance, LeaveType


class Command(BaseCommand):
    help = (
        "Create one balance per active employee and leave type for a year, "
        "including capped carry-over. Idempotent: existing rows are kept."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Year to allocate (defaults to the current year).",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        year = options["year"] or timezone.localdate().year
        employees = list(Employee.objects.filter(status=Employee.Status.ACTIVE))
        leave_types = list(LeaveType.objects.all())

        created = 0
        for employee in employees:
            for leave_type in leave_types:
                carry = self._carry_over(employee, leave_type, year)
                _, was_created = LeaveBalance.objects.get_or_create(
                    employee=employee,
                    leave_type=leave_type,
                    year=year,
                    defaults={"allocated": leave_type.annual_days + carry},
                )
                created += int(was_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Allocated {year}: {created} new balance(s) for "
                f"{len(employees)} employee(s) and {len(leave_types)} leave type(s)."
            )
        )

    @staticmethod
    def _carry_over(employee, leave_type, year: int) -> Decimal:
        if leave_type.carry_over_max <= 0:
            return Decimal("0")
        previous = LeaveBalance.objects.filter(
            employee=employee, leave_type=leave_type, year=year - 1
        ).first()
        if previous is None:
            return Decimal("0")
        return min(max(previous.remaining, Decimal("0")), leave_type.carry_over_max)
