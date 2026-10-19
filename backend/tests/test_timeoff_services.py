"""Tests for timeoff/services.py, written before the implementation.

These pin the rules from the Handbook: working days are Mon-Fri minus holidays,
half a day is 0.5, approvals deduct, rejections and cancellations give back,
overlaps and overruns are refused, and every state change is audited.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.timeoff import services
from apps.timeoff.models import LeaveBalance, LeaveRequest, LeaveType

YEAR = 2026
MONDAY = date(2026, 5, 4)
TUESDAY = date(2026, 5, 5)
HOLIDAY_WEDNESDAY = date(2026, 5, 6)
THURSDAY = date(2026, 5, 7)
FRIDAY = date(2026, 5, 8)
SATURDAY = date(2026, 5, 9)
SUNDAY = date(2026, 5, 10)
NEXT_MONDAY = date(2026, 5, 11)
LATER_MONDAY = date(2026, 6, 1)


def make_request(employee, leave_type, start=MONDAY, end=FRIDAY, half_day=False):
    return services.request_leave(
        employee=employee,
        leave_type=leave_type,
        start_date=start,
        end_date=end,
        half_day=half_day,
    )


def balance(employee, leave_type):
    return LeaveBalance.objects.get(
        employee=employee, leave_type=leave_type, year=YEAR
    )


@pytest.mark.django_db
class TestCountWorkingDays:
    def test_a_full_week_is_five_days(self):
        assert services.count_working_days(MONDAY, FRIDAY) == Decimal("5")

    def test_weekends_are_not_counted(self):
        assert services.count_working_days(MONDAY, SUNDAY) == Decimal("5")

    def test_holidays_are_not_counted(self, leave_org):
        assert services.count_working_days(MONDAY, FRIDAY) == Decimal("4")

    def test_a_single_saturday_is_zero(self):
        assert services.count_working_days(SATURDAY, SATURDAY) == Decimal("0")

    def test_a_half_day_is_half_a_day(self):
        assert services.count_working_days(TUESDAY, TUESDAY, half_day=True) == Decimal(
            "0.5"
        )

    def test_a_half_day_on_a_holiday_is_zero(self, leave_org):
        assert services.count_working_days(
            HOLIDAY_WEDNESDAY, HOLIDAY_WEDNESDAY, half_day=True
        ) == Decimal("0")

    def test_end_before_start_is_rejected(self):
        with pytest.raises(ValidationError):
            services.count_working_days(FRIDAY, MONDAY)

    def test_a_half_day_cannot_span_dates(self):
        with pytest.raises(ValidationError):
            services.count_working_days(MONDAY, TUESDAY, half_day=True)


class TestRequestLeave:
    def test_creates_a_pending_request_with_the_working_day_count(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)

        assert request.status == LeaveRequest.Status.PENDING
        assert request.days == Decimal("4")  # Mon-Fri minus the holiday
        assert request.reviewer is None
        assert balance(leave_org.org.esha, leave_org.types.annual).used == Decimal("0")

    def test_a_half_day_costs_half(self, leave_org):
        request = make_request(
            leave_org.org.esha,
            leave_org.types.annual,
            start=TUESDAY,
            end=TUESDAY,
            half_day=True,
        )

        assert request.days == Decimal("0.5")

    def test_end_before_start_is_rejected(self, leave_org):
        with pytest.raises(ValidationError):
            make_request(
                leave_org.org.esha,
                leave_org.types.annual,
                start=FRIDAY,
                end=MONDAY,
            )

    def test_a_request_cannot_span_two_years(self, leave_org):
        with pytest.raises(ValidationError, match="calendar years"):
            make_request(
                leave_org.org.esha,
                leave_org.types.annual,
                start=date(2025, 12, 29),
                end=date(2026, 1, 2),
            )

    def test_a_half_day_must_be_one_date(self, leave_org):
        with pytest.raises(ValidationError, match="single date"):
            make_request(
                leave_org.org.esha,
                leave_org.types.annual,
                start=MONDAY,
                end=TUESDAY,
                half_day=True,
            )

    def test_dates_with_no_working_days_are_rejected(self, leave_org):
        with pytest.raises(ValidationError, match="no working days"):
            make_request(
                leave_org.org.esha,
                leave_org.types.annual,
                start=SATURDAY,
                end=SUNDAY,
            )

    def test_a_balance_overrun_is_rejected_at_request_time(self, leave_org):
        LeaveBalance.objects.filter(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            year=YEAR,
        ).update(allocated=Decimal("3"))

        with pytest.raises(ValidationError, match="remaining"):
            make_request(leave_org.org.esha, leave_org.types.annual)

    def test_a_missing_balance_is_explained(self, leave_org):
        extra_type = LeaveType.objects.create(name="Study", annual_days=5)

        with pytest.raises(ValidationError, match="balance"):
            make_request(leave_org.org.esha, extra_type)

    def test_an_overlap_with_a_pending_request_is_rejected(self, leave_org):
        make_request(leave_org.org.esha, leave_org.types.annual)

        with pytest.raises(ValidationError, match="overlap"):
            make_request(
                leave_org.org.esha,
                leave_org.types.sick,
                start=THURSDAY,
                end=NEXT_MONDAY,
            )
        assert LeaveRequest.objects.filter(employee=leave_org.org.esha).count() == 1

    def test_a_cancelled_request_does_not_block_new_dates(self, leave_org):
        first = make_request(leave_org.org.esha, leave_org.types.annual)
        first.status = LeaveRequest.Status.CANCELLED
        first.save(update_fields=["status"])

        second = make_request(
            leave_org.org.esha,
            leave_org.types.annual,
            start=THURSDAY,
            end=NEXT_MONDAY,
        )

        assert second.pk != first.pk

    def test_a_type_without_approval_is_approved_immediately(self, leave_org):
        automatic = LeaveType.objects.create(
            name="Flexible",
            annual_days=Decimal("5"),
            requires_approval=False,
        )
        LeaveBalance.objects.create(
            employee=leave_org.org.meera,
            leave_type=automatic,
            year=YEAR,
            allocated=Decimal("5"),
        )

        request = make_request(leave_org.org.meera, automatic)

        assert request.status == LeaveRequest.Status.APPROVED
        assert request.reviewer is None
        assert balance(leave_org.org.meera, automatic).used == Decimal("4")


class TestApproveLeave:
    def test_a_manager_approves_and_the_balance_is_deducted(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)

        approved = services.approve_leave(
            request_id=request.pk, reviewer=leave_org.org.manager_user, comment="Enjoy"
        )

        assert approved.status == LeaveRequest.Status.APPROVED
        assert approved.reviewer == leave_org.org.meera
        assert approved.review_comment == "Enjoy"
        assert balance(leave_org.org.esha, leave_org.types.annual).used == Decimal("4")

    def test_approving_twice_does_not_deduct_twice(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)
        services.approve_leave(
            request_id=request.pk, reviewer=leave_org.org.manager_user
        )

        with pytest.raises(ValidationError, match="approved"):
            services.approve_leave(
                request_id=request.pk, reviewer=leave_org.org.manager_user
            )

        assert balance(leave_org.org.esha, leave_org.types.annual).used == Decimal("4")

    def test_an_approval_that_would_overdraw_is_refused(self, leave_org):
        LeaveBalance.objects.filter(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            year=YEAR,
        ).update(allocated=Decimal("6"))
        first = make_request(
            leave_org.org.esha, leave_org.types.annual, start=MONDAY, end=FRIDAY
        )
        second = make_request(
            leave_org.org.esha,
            leave_org.types.annual,
            start=NEXT_MONDAY,
            end=date(2026, 5, 15),
        )

        services.approve_leave(
            request_id=first.pk, reviewer=leave_org.org.manager_user
        )

        with pytest.raises(ValidationError, match="remaining"):
            services.approve_leave(
                request_id=second.pk, reviewer=leave_org.org.manager_user
            )
        second.refresh_from_db()
        assert second.status == LeaveRequest.Status.PENDING
        assert balance(leave_org.org.esha, leave_org.types.annual).used == Decimal("4")

    def test_a_manager_cannot_approve_another_team(self, leave_org):
        request = make_request(leave_org.org.sam, leave_org.types.annual)

        with pytest.raises(PermissionDenied):
            services.approve_leave(
                request_id=request.pk, reviewer=leave_org.org.manager_user
            )

    def test_an_employee_cannot_approve_their_own_leave(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)

        with pytest.raises(PermissionDenied):
            services.approve_leave(
                request_id=request.pk, reviewer=leave_org.org.employee_user
            )

    def test_hr_can_approve_anyone(self, leave_org):
        request = make_request(leave_org.org.sam, leave_org.types.annual)

        approved = services.approve_leave(
            request_id=request.pk, reviewer=leave_org.org.hr
        )

        assert approved.status == LeaveRequest.Status.APPROVED
        assert approved.reviewer is None  # HR has no employee record in this fixture

    def test_admin_can_approve(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)

        approved = services.approve_leave(
            request_id=request.pk, reviewer=leave_org.org.admin
        )

        assert approved.status == LeaveRequest.Status.APPROVED

    def test_a_rejected_request_cannot_be_approved(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)
        services.reject_leave(
            request_id=request.pk,
            reviewer=leave_org.org.manager_user,
            comment="Not now",
        )

        with pytest.raises(ValidationError, match="rejected"):
            services.approve_leave(
                request_id=request.pk, reviewer=leave_org.org.manager_user
            )


class TestRejectLeave:
    def test_rejecting_keeps_the_balance_and_records_the_comment(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)

        rejected = services.reject_leave(
            request_id=request.pk,
            reviewer=leave_org.org.manager_user,
            comment="Team offsite that week",
        )

        assert rejected.status == LeaveRequest.Status.REJECTED
        assert rejected.reviewer == leave_org.org.meera
        assert rejected.review_comment == "Team offsite that week"
        assert balance(leave_org.org.esha, leave_org.types.annual).used == Decimal("0")

    def test_a_comment_is_required_to_reject(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)

        with pytest.raises(ValidationError) as excinfo:
            services.reject_leave(
                request_id=request.pk,
                reviewer=leave_org.org.manager_user,
                comment="   ",
            )

        assert "comment" in excinfo.value.detail

    def test_an_approved_request_cannot_be_rejected(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)
        services.approve_leave(
            request_id=request.pk, reviewer=leave_org.org.manager_user
        )

        with pytest.raises(ValidationError, match="approved"):
            services.reject_leave(
                request_id=request.pk,
                reviewer=leave_org.org.manager_user,
                comment="Too late",
            )


class TestCancelLeave:
    def test_cancelling_a_pending_request_changes_nothing_else(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)

        cancelled = services.cancel_leave(
            request_id=request.pk, actor=leave_org.org.employee_user
        )

        assert cancelled.status == LeaveRequest.Status.CANCELLED
        assert balance(leave_org.org.esha, leave_org.types.annual).used == Decimal("0")

    def test_cancelling_an_approved_request_returns_the_balance(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)
        services.approve_leave(
            request_id=request.pk, reviewer=leave_org.org.manager_user
        )
        assert balance(leave_org.org.esha, leave_org.types.annual).used == Decimal("4")

        services.cancel_leave(request_id=request.pk, actor=leave_org.org.employee_user)

        assert balance(leave_org.org.esha, leave_org.types.annual).used == Decimal("0")

    def test_only_the_owner_may_cancel(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)

        with pytest.raises(PermissionDenied):
            services.cancel_leave(
                request_id=request.pk, actor=leave_org.org.manager_user
            )

    def test_an_admin_may_cancel_anyone(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)

        cancelled = services.cancel_leave(
            request_id=request.pk, actor=leave_org.org.admin
        )

        assert cancelled.status == LeaveRequest.Status.CANCELLED

    def test_a_rejected_request_cannot_be_cancelled(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)
        services.reject_leave(
            request_id=request.pk,
            reviewer=leave_org.org.manager_user,
            comment="No",
        )

        with pytest.raises(ValidationError, match="rejected"):
            services.cancel_leave(
                request_id=request.pk, actor=leave_org.org.employee_user
            )

    def test_cancelling_twice_is_refused(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)
        services.cancel_leave(request_id=request.pk, actor=leave_org.org.employee_user)

        with pytest.raises(ValidationError, match="cancelled"):
            services.cancel_leave(
                request_id=request.pk, actor=leave_org.org.employee_user
            )


class TestPreview:
    def test_returns_days_and_remaining(self, leave_org):
        preview = services.preview_leave(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            start_date=MONDAY,
            end_date=FRIDAY,
        )

        assert preview["days"] == Decimal("4")
        assert preview["remaining"] == Decimal("20")
        assert preview["sufficient"] is True
        assert preview["overlap"] is False

    def test_flags_an_insufficient_balance(self, leave_org):
        LeaveBalance.objects.filter(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            year=YEAR,
        ).update(allocated=Decimal("2"))

        preview = services.preview_leave(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            start_date=MONDAY,
            end_date=FRIDAY,
        )

        assert preview["sufficient"] is False

    def test_flags_an_overlap(self, leave_org):
        make_request(leave_org.org.esha, leave_org.types.annual)

        preview = services.preview_leave(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            start_date=THURSDAY,
            end_date=NEXT_MONDAY,
        )

        assert preview["overlap"] is True


class TestAllocateBalances:
    def test_creates_a_balance_per_active_employee_and_type(self, leave_org):
        from django.core.management import call_command

        LeaveBalance.objects.all().delete()

        call_command("allocate_balances", year=YEAR)

        assert LeaveBalance.objects.filter(year=YEAR).count() == 3 * 3

    def test_is_idempotent(self, leave_org):
        from django.core.management import call_command

        LeaveBalance.objects.all().delete()
        call_command("allocate_balances", year=YEAR)
        call_command("allocate_balances", year=YEAR)

        assert LeaveBalance.objects.filter(year=YEAR).count() == 3 * 3

    def test_carries_over_unused_days_up_to_the_cap(self, leave_org):
        from django.core.management import call_command

        LeaveBalance.objects.all().delete()
        # Last year: 20 allocated, 2 used -> 18 unused, cap is 5 for annual.
        LeaveBalance.objects.create(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            year=2025,
            allocated=Decimal("20"),
            used=Decimal("2"),
        )

        call_command("allocate_balances", year=YEAR)

        current = balance(leave_org.org.esha, leave_org.types.annual)
        assert current.allocated == Decimal("25")  # 20 + capped 5

    def test_does_not_overwrite_an_existing_allocation(self, leave_org):
        from django.core.management import call_command

        current = balance(leave_org.org.esha, leave_org.types.annual)
        current.allocated = Decimal("13")
        current.save(update_fields=["allocated"])

        call_command("allocate_balances", year=YEAR)

        current.refresh_from_db()
        assert current.allocated == Decimal("13")

    def test_skips_inactive_employees(self, leave_org):
        from django.core.management import call_command

        LeaveBalance.objects.all().delete()
        leave_org.org.sam.status = "inactive"
        leave_org.org.sam.save(update_fields=["status"])

        call_command("allocate_balances", year=YEAR)

        assert not LeaveBalance.objects.filter(employee=leave_org.org.sam).exists()


class TestAudit:
    def test_requesting_writes_one_create_row(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)

        rows = AuditLog.objects.filter(
            model="timeoff.leaverequest", object_id=str(request.pk)
        )
        assert rows.count() == 1
        assert rows.get().action == "create"
        assert rows.get().changes["after"]["days"] == "4"

    def test_approving_writes_one_update_row_with_the_status_change(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)
        rows = AuditLog.objects.filter(
            model="timeoff.leaverequest", object_id=str(request.pk)
        )

        services.approve_leave(
            request_id=request.pk,
            reviewer=leave_org.org.manager_user,
            comment="Fine",
        )

        updates = rows.filter(action="update")
        assert updates.count() == 1
        assert updates.get().changes["changes"]["status"] == {
            "before": "pending",
            "after": "approved",
        }

    def test_cancelling_an_approved_request_is_audited(self, leave_org):
        request = make_request(leave_org.org.esha, leave_org.types.annual)
        services.approve_leave(
            request_id=request.pk, reviewer=leave_org.org.manager_user
        )

        services.cancel_leave(request_id=request.pk, actor=leave_org.org.employee_user)

        rows = AuditLog.objects.filter(
            model="timeoff.leaverequest", object_id=str(request.pk), action="update"
        )
        assert rows.count() == 2  # approve, then cancel
        latest = rows.order_by("-id").first()
        assert latest.changes["changes"]["status"] == {
            "before": "approved",
            "after": "cancelled",
        }


@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="The exclusion constraint is Postgres-only; SQLite has no GiST.",
)
class TestDatabaseOverlapConstraint:
    def test_the_database_refuses_overlapping_requests(self, leave_org):
        LeaveRequest.objects.create(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            start_date=MONDAY,
            end_date=FRIDAY,
            days=Decimal("4"),
        )

        with pytest.raises(IntegrityError), transaction.atomic():
            LeaveRequest.objects.create(
                employee=leave_org.org.esha,
                leave_type=leave_org.types.annual,
                start_date=THURSDAY,
                end_date=NEXT_MONDAY,
                days=Decimal("2"),
            )

    def test_cancelled_requests_do_not_block_dates(self, leave_org):
        LeaveRequest.objects.create(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            start_date=MONDAY,
            end_date=FRIDAY,
            days=Decimal("4"),
            status=LeaveRequest.Status.CANCELLED,
        )

        overlap = LeaveRequest.objects.create(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            start_date=THURSDAY,
            end_date=NEXT_MONDAY,
            days=Decimal("2"),
        )

        assert overlap.pk is not None
