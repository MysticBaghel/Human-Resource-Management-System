"""Shared demo reference data for the seed commands."""

from datetime import date
from decimal import Decimal

from .models import Holiday, LeaveType

DEMO_LEAVE_TYPES = [
    {"name": "Annual", "annual_days": "20", "carry_over_max": "5"},
    {"name": "Sick", "annual_days": "10"},
    {"name": "Unpaid", "annual_days": "10", "is_paid": False},
]

DEMO_HOLIDAYS = {
    (1, 1): "New Year's Day",
    (5, 1): "Labour Day",
    (8, 15): "Independence Day",
    (12, 25): "Christmas Day",
}


def ensure_leave_types() -> dict[str, LeaveType]:
    types: dict[str, LeaveType] = {}
    for data in DEMO_LEAVE_TYPES:
        defaults = {
            "annual_days": Decimal(data["annual_days"]),
            "carry_over_max": Decimal(data.get("carry_over_max", "0")),
            "is_paid": data.get("is_paid", True),
        }
        leave_type, _ = LeaveType.objects.get_or_create(
            name=data["name"], defaults=defaults
        )
        types[data["name"]] = leave_type
    return types


def ensure_holidays(year: int) -> None:
    for (month, day), name in DEMO_HOLIDAYS.items():
        Holiday.objects.get_or_create(
            date=date(year, month, day), defaults={"name": name}
        )
