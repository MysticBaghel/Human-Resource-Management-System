"""All time-off rules live here.

Working-day counting, overlap checks, balance checks and every status change.
Views validate shape and call these functions; nothing else moves a balance.

Balance and request rows are locked with ``select_for_update()`` inside one
transaction, so two reviewers cannot deduct the same days twice. On SQLite the
lock is a no-op, which is why the concurrency rule is also covered by the
Postgres-only database test.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import User

from .models import Holiday, LeaveBalance, LeaveRequest

HALF_DAY = Decimal("0.5")
REVIEWER_ROLES = frozenset({User.Role.MANAGER, User.Role.HR, User.Role.ADMIN})


def count_working_days(start_date, end_date, half_day: bool = False) -> Decimal:
    """Working days in an inclusive range: Mon-Fri minus company holidays.

    A half day only makes sense on a single date and costs 0.5; a half day on a
    weekend or holiday costs nothing, and the caller refuses the request.
    """
    if end_date < start_date:
        raise ValidationError("The end date cannot be before the start date.")

    if half_day:
        if start_date != end_date:
            raise ValidationError("A half day must start and end on a single date.")
        if not _is_working_day(start_date):
            return Decimal("0")
        return HALF_DAY

    holidays = set(
        Holiday.objects.filter(date__range=(start_date, end_date)).values_list(
            "date", flat=True
        )
    )
    days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5 and current not in holidays:
            days += 1
        current += timedelta(days=1)
    return Decimal(days)


def request_leave(
    *,
    employee,
    leave_type,
    start_date,
    end_date,
    half_day: bool = False,
) -> LeaveRequest:
    """Validate a request and create it, pending unless the type needs no approval."""
    if end_date < start_date:
        raise ValidationError("The end date cannot be before the start date.")
    if not employee.is_active:
        raise ValidationError("Deactivated employees cannot request leave.")
    if start_date.year != end_date.year:
        raise ValidationError("A leave request cannot span two calendar years.")

    days = count_working_days(start_date, end_date, half_day)
    if days <= 0:
        raise ValidationError("The selected dates contain no working days.")

    existing = _overlapping_request(employee, start_date, end_date)
    if existing is not None:
        raise ValidationError(_overlap_message(existing))

    with transaction.atomic():
        balance = _balance_for(employee, leave_type, start_date.year, lock=True)
        remaining = balance.remaining
        if days > remaining:
            raise ValidationError(_insufficient_message(leave_type, remaining, days))

        # A type that needs no approval is deducted and approved in one save,
        # so the audit trail still shows a single create.
        status = (
            LeaveRequest.Status.PENDING
            if leave_type.requires_approval
            else LeaveRequest.Status.APPROVED
        )
        if status == LeaveRequest.Status.APPROVED:
            balance.used = balance.used + days
            balance.save(update_fields=["used"])

        try:
            return LeaveRequest.objects.create(
                employee=employee,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                half_day=half_day,
                days=days,
                status=status,
            )
        except IntegrityError as exc:
            # The database's exclusion constraint won a race with the check
            # above. Roll back the balance movement with the same exception.
            raise ValidationError(_overlap_message_for_dates(start_date, end_date)) from exc


def approve_leave(*, request_id: int, reviewer, comment: str = "") -> LeaveRequest:
    """Approve a pending request and deduct its days, once."""
    with transaction.atomic():
        leave = _locked_request(request_id)
        _ensure_can_review(reviewer, leave)
        if leave.status != LeaveRequest.Status.PENDING:
            raise ValidationError(_already(leave, "approved"))

        balance = _balance_for(
            leave.employee, leave.leave_type, leave.start_date.year, lock=True
        )
        remaining = balance.remaining
        if leave.days > remaining:
            raise ValidationError(
                _insufficient_message(leave.leave_type, remaining, leave.days)
            )

        balance.used = balance.used + leave.days
        balance.save(update_fields=["used"])

        leave.status = LeaveRequest.Status.APPROVED
        leave.reviewer = _reviewer_employee(reviewer)
        leave.review_comment = (comment or "").strip()
        leave.save(update_fields=["status", "reviewer", "review_comment"])
        return leave


def reject_leave(*, request_id: int, reviewer, comment: str) -> LeaveRequest:
    """Reject a pending request. No balance moves, which is the whole point."""
    if not (comment or "").strip():
        raise ValidationError(
            {"comment": ["A comment is required when rejecting a request."]}
        )

    with transaction.atomic():
        leave = _locked_request(request_id)
        _ensure_can_review(reviewer, leave)
        if leave.status != LeaveRequest.Status.PENDING:
            raise ValidationError(_already(leave, "rejected"))

        leave.status = LeaveRequest.Status.REJECTED
        leave.reviewer = _reviewer_employee(reviewer)
        leave.review_comment = comment.strip()
        leave.save(update_fields=["status", "reviewer", "review_comment"])
        return leave


def cancel_leave(*, request_id: int, actor) -> LeaveRequest:
    """Cancel pending or approved leave; an approved one gives its days back."""
    with transaction.atomic():
        leave = _locked_request(request_id)
        if getattr(actor, "role", None) != User.Role.ADMIN and leave.employee.user_id != actor.pk:
            raise PermissionDenied("You can only cancel your own leave.")
        if leave.status not in {
            LeaveRequest.Status.PENDING,
            LeaveRequest.Status.APPROVED,
        }:
            raise ValidationError(_already(leave, "cancelled"))

        if leave.status == LeaveRequest.Status.APPROVED:
            balance = _balance_for(
                leave.employee, leave.leave_type, leave.start_date.year, lock=True
            )
            balance.used = balance.used - leave.days
            balance.save(update_fields=["used"])

        leave.status = LeaveRequest.Status.CANCELLED
        leave.save(update_fields=["status"])
        return leave


def preview_leave(
    *,
    employee,
    leave_type,
    start_date,
    end_date,
    half_day: bool = False,
) -> dict:
    """What a request would cost, without creating anything.

    The React dialog calls this so day counting stays server-side and holidays
    are respected in the live preview.
    """
    if end_date < start_date:
        raise ValidationError("The end date cannot be before the start date.")
    if start_date.year != end_date.year:
        raise ValidationError("A leave request cannot span two calendar years.")

    days = count_working_days(start_date, end_date, half_day)
    balance = LeaveBalance.objects.filter(
        employee=employee, leave_type=leave_type, year=start_date.year
    ).first()
    remaining = balance.remaining if balance is not None else None
    return {
        "days": days,
        "remaining": remaining,
        "sufficient": remaining is not None and days <= remaining,
        "overlap": _overlapping_request(employee, start_date, end_date) is not None,
    }


def _is_working_day(day) -> bool:
    return day.weekday() < 5 and not Holiday.objects.filter(date=day).exists()


def _locked_request(request_id: int) -> LeaveRequest:
    """Lock the request row itself.

    Deliberately no select_related: a join to the nullable employee.team would
    make Postgres refuse the lock ("FOR UPDATE cannot be applied to the nullable
    side of an outer join"). The relations are read inside the transaction and
    are not part of the lock.
    """
    try:
        return LeaveRequest.objects.select_for_update().get(pk=request_id)
    except LeaveRequest.DoesNotExist as exc:
        raise NotFound("This leave request does not exist.") from exc


def _balance_for(employee, leave_type, year: int, *, lock: bool = False) -> LeaveBalance:
    queryset = LeaveBalance.objects
    if lock:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(employee=employee, leave_type=leave_type, year=year)
    except LeaveBalance.DoesNotExist as exc:
        raise ValidationError(
            f"No {leave_type.name} balance is allocated for {year}. "
            "Ask HR to allocate balances."
        ) from exc


def _overlapping_request(employee, start_date, end_date):
    return (
        LeaveRequest.objects.filter(
            employee=employee,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        .exclude(status=LeaveRequest.Status.CANCELLED)
        .select_related("leave_type")
        .first()
    )


def _overlap_message(existing: LeaveRequest) -> str:
    return (
        f"These dates overlap an existing {existing.leave_type.name} request "
        f"({existing.start_date:%d %b %Y} – {existing.end_date:%d %b %Y})."
    )


def _overlap_message_for_dates(start_date, end_date) -> str:
    return (
        f"These dates overlap an existing request "
        f"({start_date:%d %b %Y} – {end_date:%d %b %Y})."
    )


def _insufficient_message(leave_type, remaining: Decimal, requested: Decimal) -> str:
    return (
        f"Not enough {leave_type.name} leave: {remaining} day(s) remaining, "
        f"{requested} requested."
    )


def _already(leave: LeaveRequest, action: str) -> str:
    return (
        f"This request is already {leave.get_status_display().lower()} "
        f"and cannot be {action}."
    )


def _reviewer_employee(reviewer):
    """The reviewer's employee record, if they have one.

    HR and admin accounts may exist without an employee record; the request is
    still attributed to the signed-in user in the audit log.
    """
    return getattr(reviewer, "employee", None)


def _ensure_can_review(reviewer, leave: LeaveRequest) -> None:
    role = getattr(reviewer, "role", None)
    if role in {User.Role.HR, User.Role.ADMIN}:
        return
    if role != User.Role.MANAGER:
        raise PermissionDenied("You do not have permission to review this request.")

    employee = _reviewer_employee(reviewer)
    if employee is None:
        raise PermissionDenied("Your account has no employee record to review with.")

    reports_to_them = leave.employee.manager_id == employee.pk
    leads_their_team = bool(
        leave.employee.team_id and leave.employee.team.lead_id == employee.pk
    )
    if not (reports_to_them or leads_their_team):
        raise PermissionDenied("Managers can only review leave for their own team.")
