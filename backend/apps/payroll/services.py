"""Payroll services: the only place salary and payroll rows are written.

Values stay ``Decimal`` end to end. Payroll records copy the salary components
at generation time, which is what makes finalized (and even draft) payroll
immutable when a salary structure is revised later.
"""

import calendar
from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.employees.models import Employee

from .models import (
    DEDUCTION_FIELDS,
    EARNING_FIELDS,
    ZERO,
    PayrollRecord,
    SalaryRevision,
    SalaryStructure,
    employee_code,
)

MIN_PAYROLL_YEAR = 2000
MAX_PAYROLL_YEAR = 2100


def _money(value: Decimal | str | int) -> Decimal:
    """Normalise a monetary value to two decimal places without floats."""
    return Decimal(value).quantize(Decimal("0.01"))


def parse_period(month: int, year: int) -> tuple[date, date]:
    """Validate a payroll period and return its first and last date."""
    if not isinstance(month, int) or not 1 <= month <= 12:
        raise ValidationError({"month": ["Choose a month between 1 and 12."]})
    if not isinstance(year, int) or not MIN_PAYROLL_YEAR <= year <= MAX_PAYROLL_YEAR:
        raise ValidationError(
            {
                "year": [
                    f"Choose a year between {MIN_PAYROLL_YEAR} and {MAX_PAYROLL_YEAR}."
                ]
            }
        )
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def period_end(month: int, year: int) -> date:
    return parse_period(month, year)[1]


def structure_totals(values: dict) -> dict[str, Decimal]:
    """Gross, deductions and net for a dict of component values."""
    gross = sum((values[name] for name in EARNING_FIELDS), ZERO)
    deductions = sum((values[name] for name in DEDUCTION_FIELDS), ZERO)
    return {
        "gross_salary": gross,
        "total_deductions": deductions,
        "net_salary": gross - deductions,
    }


def snapshot_structure(structure: SalaryStructure) -> dict:
    """A JSON-safe snapshot of every value that matters for history."""
    values = {
        name: str(getattr(structure, name))
        for name in (*EARNING_FIELDS, *DEDUCTION_FIELDS)
    }
    values.update(
        {
            "gross_salary": str(structure.gross_salary),
            "total_deductions": str(structure.total_deductions),
            "net_salary": str(structure.net_salary),
            "effective_date": structure.effective_date.isoformat(),
            "is_active": structure.is_active,
        }
    )
    return values


def applicable_structure(
    employee: Employee, for_period_end: date
) -> SalaryStructure | None:
    """The structure that applied at the end of a payroll period.

    Structure versions have increasing effective dates. The newest version on
    or before the period end is the one that was in force then.

    Revoking a structure keeps it for history but stops it being used for
    periods after the revocation date. Periods that ended before the revoke
    still resolve to it, so payroll generated earlier (or for an earlier month)
    is not invalidated.
    """
    structure = (
        SalaryStructure.objects.filter(
            employee=employee, effective_date__lte=for_period_end
        )
        .order_by("-effective_date", "-id")
        .first()
    )
    if structure is None:
        return None
    if structure.revoked_at is not None and structure.revoked_at <= for_period_end:
        return None
    return structure


def _validate_totals(values: dict) -> None:
    totals = structure_totals(values)
    if totals["net_salary"] < 0:
        raise ValidationError(
            {
                "other_deductions": [
                    "Total deductions cannot be greater than gross salary."
                ]
            }
        )


@transaction.atomic
def create_salary_structure(*, actor, data: dict) -> SalaryStructure:
    """Create the first (active) salary structure for an employee."""
    employee = data["employee"]
    if (
        SalaryStructure.objects.select_for_update()
        .filter(employee=employee, is_active=True)
        .exists()
    ):
        raise ValidationError(
            {"employee": ["This employee already has an active salary structure."]}
        )

    values = {
        name: data.get(name, ZERO) for name in (*EARNING_FIELDS, *DEDUCTION_FIELDS)
    }
    _validate_totals(values)

    structure = SalaryStructure(
        employee=employee,
        effective_date=data["effective_date"],
        created_by=actor,
        **values,
    )
    try:
        structure.save()
    except IntegrityError as exc:
        raise ValidationError(
            {"employee": ["This employee already has an active salary structure."]}
        ) from exc
    return structure


@transaction.atomic
def revise_salary_structure(
    *, structure: SalaryStructure, actor, data: dict
) -> tuple[SalaryStructure, SalaryRevision | None]:
    """Create a new version of a salary structure and record the revision.

    The previous row is kept and marked inactive. A revision cannot move the
    effective date backwards: that would make "newest effective date wins"
    ambiguous for payroll periods in between.
    """
    locked = SalaryStructure.objects.select_for_update().get(pk=structure.pk)
    if not locked.is_active:
        raise ValidationError(
            {"detail": ["Only the employee's active salary structure can be revised."]}
        )

    new_effective_date = data.get("effective_date", locked.effective_date)
    if new_effective_date < locked.effective_date:
        raise ValidationError(
            {
                "effective_date": [
                    "A revision cannot take effect before the current structure."
                ]
            }
        )

    values = {
        name: data.get(name, getattr(locked, name))
        for name in (*EARNING_FIELDS, *DEDUCTION_FIELDS)
    }
    _validate_totals(values)

    unchanged = new_effective_date == locked.effective_date and all(
        getattr(locked, name) == values[name] for name in values
    )
    if unchanged:
        return locked, None

    previous_values = snapshot_structure(locked)

    # Deactivate first: the partial unique constraint allows only one active
    # row per employee, so creating the replacement before this save would
    # violate it.
    locked.is_active = False
    locked.save(update_fields=["is_active", "updated_at"])

    new_structure = SalaryStructure(
        employee=locked.employee,
        effective_date=new_effective_date,
        is_active=True,
        created_by=actor,
        **values,
    )
    try:
        new_structure.save()
    except IntegrityError as exc:
        raise ValidationError(
            {"detail": ["Another revision landed first. Reload and try again."]}
        ) from exc

    revision = SalaryRevision.objects.create(
        employee=locked.employee,
        previous_structure=locked,
        new_structure=new_structure,
        previous_values=previous_values,
        new_values=snapshot_structure(new_structure),
        effective_date=new_effective_date,
        updated_by=actor,
        reason=data.get("reason", ""),
    )
    return new_structure, revision


@transaction.atomic
def revoke_salary_structure(*, structure: SalaryStructure, actor) -> SalaryStructure:
    """Retire the employee's active salary structure without deleting history.

    The row stays in the database (and in revision history) but is no longer
    active, so it disappears from the salary-structure page and cannot be used
    by payroll periods after today. Creating a new structure for the employee
    is then allowed.
    """
    locked = SalaryStructure.objects.select_for_update().get(pk=structure.pk)
    if not locked.is_active:
        raise ValidationError(
            {"detail": ["Only the active salary structure can be revoked."]}
        )

    locked.is_active = False
    locked.revoked_at = timezone.localdate()
    locked.save(update_fields=["is_active", "revoked_at", "updated_at"])
    return locked


def _payroll_defaults(
    *,
    employee: Employee,
    structure: SalaryStructure,
    month: int,
    year: int,
    actor,
) -> dict:
    """Snapshot fields for a new payroll record, copied from the structure.

    The employee and period are lookup keys in ``get_or_create`` and are
    deliberately not repeated here.
    """
    record = PayrollRecord(
        employee=employee,
        salary_structure=structure,
        payroll_month=month,
        payroll_year=year,
        payslip_number=f"PAY-{year}{month:02d}-{employee.pk:06d}",
        employee_name=employee.full_name,
        employee_code=employee_code(employee.pk),
        designation=employee.job_title,
        department=employee.team.name if employee.team_id else "",
        date_of_joining=employee.start_date,
        generated_by=actor,
        adjustment_amount=ZERO,
        **{
            name: getattr(structure, name)
            for name in (*EARNING_FIELDS, *DEDUCTION_FIELDS)
        },
    )
    record.recalculate()
    return {
        "salary_structure": structure,
        "payslip_number": record.payslip_number,
        "employee_name": record.employee_name,
        "employee_code": record.employee_code,
        "designation": record.designation,
        "department": record.department,
        "date_of_joining": record.date_of_joining,
        "gross_salary": record.gross_salary,
        "total_deductions": record.total_deductions,
        "adjustment_amount": record.adjustment_amount,
        "adjustment_note": record.adjustment_note,
        "net_salary": record.net_salary,
        "generated_by": actor,
        **{
            name: getattr(record, name) for name in (*EARNING_FIELDS, *DEDUCTION_FIELDS)
        },
    }


@transaction.atomic
def generate_payroll(
    *, actor, month: int, year: int, employee: Employee | None = None
) -> dict:
    """Generate draft payroll for one employee, or every eligible employee.

    Duplicate prevention is both a pre-check and a database unique constraint.
    In bulk mode an existing record is reported as skipped rather than aborting
    the whole run.
    """
    _, end = parse_period(month, year)

    if employee is not None:
        if employee.status != Employee.Status.ACTIVE:
            raise ValidationError("Only active employees can be paid.")
        if employee.start_date > end:
            raise ValidationError(
                "This employee has not started by the end of the payroll period."
            )

        structure = applicable_structure(employee, end)
        if structure is None:
            raise ValidationError(
                "This employee has no salary structure applicable to the period."
            )

        record, created = PayrollRecord.objects.get_or_create(
            employee=employee,
            payroll_year=year,
            payroll_month=month,
            defaults=_payroll_defaults(
                employee=employee,
                structure=structure,
                month=month,
                year=year,
                actor=actor,
            ),
        )
        if not created:
            raise ValidationError(
                "Payroll already exists for this employee and pay period."
            )
        return {
            "generated": [record],
            "skipped": [],
            "generated_count": 1,
            "skipped_count": 0,
        }

    employees = (
        Employee.objects.filter(status=Employee.Status.ACTIVE, start_date__lte=end)
        .select_related("team", "user")
        .order_by("first_name", "last_name")
    )

    generated: list[PayrollRecord] = []
    skipped: list[dict] = []
    for person in employees:
        structure = applicable_structure(person, end)
        if structure is None:
            skipped.append(
                {
                    "employee": person.pk,
                    "employee_name": person.full_name,
                    "reason": "No salary structure applicable to the period.",
                }
            )
            continue

        record, created = PayrollRecord.objects.get_or_create(
            employee=person,
            payroll_year=year,
            payroll_month=month,
            defaults=_payroll_defaults(
                employee=person,
                structure=structure,
                month=month,
                year=year,
                actor=actor,
            ),
        )
        if created:
            generated.append(record)
        else:
            skipped.append(
                {
                    "employee": person.pk,
                    "employee_name": person.full_name,
                    "reason": "Payroll already exists for this period.",
                }
            )

    return {
        "generated": generated,
        "skipped": skipped,
        "generated_count": len(generated),
        "skipped_count": len(skipped),
    }


@transaction.atomic
def adjust_payroll(
    *, record: PayrollRecord, adjustment_amount: Decimal, adjustment_note: str
) -> PayrollRecord:
    """Change a draft record's adjustment. Finalized records never change."""
    locked = PayrollRecord.objects.select_for_update().get(pk=record.pk)
    if locked.status == PayrollRecord.Status.FINALIZED:
        raise ValidationError(
            {"detail": ["A finalized payroll record cannot be adjusted."]}
        )

    locked.adjustment_amount = _money(adjustment_amount)
    locked.adjustment_note = adjustment_note
    locked.recalculate()
    if locked.net_salary < 0:
        raise ValidationError(
            {"adjustment_amount": ["The adjustment makes net salary negative."]}
        )
    locked.save(
        update_fields=[
            "adjustment_amount",
            "adjustment_note",
            "gross_salary",
            "total_deductions",
            "net_salary",
            "updated_at",
        ]
    )
    return locked


@transaction.atomic
def finalize_payroll(*, record: PayrollRecord, actor) -> PayrollRecord:
    """Finalize one draft record and freeze its snapshot."""
    locked = PayrollRecord.objects.select_for_update().get(pk=record.pk)
    if locked.status == PayrollRecord.Status.FINALIZED:
        raise ValidationError({"detail": ["This payroll record is already finalized."]})

    locked.status = PayrollRecord.Status.FINALIZED
    locked.finalized_by = actor
    locked.finalized_at = timezone.now()
    locked.save(update_fields=["status", "finalized_by", "finalized_at", "updated_at"])
    return locked


@transaction.atomic
def finalize_payroll_period(*, month: int, year: int, actor) -> list[PayrollRecord]:
    """Finalize every draft record for a period in one transaction."""
    parse_period(month, year)
    records = list(
        PayrollRecord.objects.select_for_update()
        .filter(
            payroll_year=year,
            payroll_month=month,
            status=PayrollRecord.Status.DRAFT,
        )
        .order_by("employee__first_name", "employee__last_name")
    )
    now = timezone.now()
    for record in records:
        record.status = PayrollRecord.Status.FINALIZED
        record.finalized_by = actor
        record.finalized_at = now
        record.save(
            update_fields=["status", "finalized_by", "finalized_at", "updated_at"]
        )
    return records


@transaction.atomic
def cancel_payroll(*, record: PayrollRecord, actor) -> PayrollRecord | None:
    """Cancel a payroll record.

    A draft is not financial data yet, so cancelling it deletes the row and
    frees the period for regeneration. A finalized record is kept for audit and
    its payment status becomes ``cancelled`` instead.
    """
    locked = PayrollRecord.objects.select_for_update().get(pk=record.pk)

    if locked.status == PayrollRecord.Status.DRAFT:
        locked.delete()
        return None

    if locked.payment_status == PayrollRecord.PaymentStatus.CANCELLED:
        raise ValidationError({"detail": ["This payroll is already cancelled."]})

    locked.payment_status = PayrollRecord.PaymentStatus.CANCELLED
    locked.payment_date = None
    locked.save(
        update_fields=["payment_status", "payment_date", "updated_at"]
    )
    return locked


@transaction.atomic
def update_payment_status(
    *,
    record: PayrollRecord,
    payment_status: str,
    payment_date: date | None,
    payment_reference: str,
) -> PayrollRecord:
    """Record the outcome of a payment. No bank or gateway call is made."""
    locked = PayrollRecord.objects.select_for_update().get(pk=record.pk)
    if locked.status != PayrollRecord.Status.FINALIZED:
        raise ValidationError(
            {"detail": ["Payment status is only recorded on finalized payroll."]}
        )

    if payment_status not in PayrollRecord.PaymentStatus.values:
        raise ValidationError({"payment_status": ["Unknown payment status."]})
    if payment_status == PayrollRecord.PaymentStatus.PAID and payment_date is None:
        raise ValidationError(
            {"payment_date": ["A paid payroll needs a payment date."]}
        )
    if payment_status in {
        PayrollRecord.PaymentStatus.PENDING,
        PayrollRecord.PaymentStatus.CANCELLED,
    }:
        payment_date = None

    locked.payment_status = payment_status
    locked.payment_date = payment_date
    locked.payment_reference = payment_reference.strip()
    locked.save(
        update_fields=[
            "payment_status",
            "payment_date",
            "payment_reference",
            "updated_at",
        ]
    )
    return locked


def build_payroll_dashboard() -> dict:
    """Metrics for the HR/admin payroll dashboard, for the current month."""
    today = timezone.localdate()
    current = PayrollRecord.objects.filter(
        payroll_year=today.year, payroll_month=today.month
    )

    def total(queryset) -> Decimal:
        value = queryset.aggregate(value=Sum("net_salary"))["value"]
        return _money(value or ZERO)

    paid = current.filter(payment_status=PayrollRecord.PaymentStatus.PAID)
    pending = current.filter(payment_status=PayrollRecord.PaymentStatus.PENDING)
    failed = current.filter(payment_status=PayrollRecord.PaymentStatus.FAILED)

    recent = PayrollRecord.objects.select_related(
        "employee", "generated_by", "finalized_by"
    ).order_by("-created_at", "-id")[:6]

    return {
        "month": today.month,
        "year": today.year,
        "employees_with_salary_structures": SalaryStructure.objects.filter(
            is_active=True
        )
        .values("employee_id")
        .distinct()
        .count(),
        "current_month_payroll_total": str(total(current)),
        "total_paid_amount": str(total(paid)),
        "pending_payments_count": pending.count(),
        "pending_payments_amount": str(total(pending)),
        "failed_payments_count": failed.count(),
        "draft_count": current.filter(status=PayrollRecord.Status.DRAFT).count(),
        "finalized_count": current.filter(
            status=PayrollRecord.Status.FINALIZED
        ).count(),
        "recent_activity": recent,
    }
