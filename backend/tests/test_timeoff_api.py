"""Time-off API tests: roles, scoping, actions, calendar and audit attribution."""

from datetime import date
from decimal import Decimal

import pytest

from apps.audit.models import AuditLog
from apps.timeoff.models import LeaveBalance, LeaveRequest

LEAVE_TYPES = "/api/v1/leave-types/"
BALANCES = "/api/v1/leave-balances/"
REQUESTS = "/api/v1/leave-requests/"
CALENDAR = "/api/v1/leave-calendar/"

MONDAY = date(2026, 5, 4)
TUESDAY = date(2026, 5, 5)
THURSDAY = date(2026, 5, 7)
FRIDAY = date(2026, 5, 8)
NEXT_MONDAY = date(2026, 5, 11)


def leave_request(
    employee,
    leave_type,
    start=MONDAY,
    end=TUESDAY,
    *,
    status=LeaveRequest.Status.PENDING,
    days=Decimal("2"),
):
    return LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=start,
        end_date=end,
        days=days,
        status=status,
    )


def create_payload(leave_type, start=MONDAY, end=FRIDAY, half_day=False):
    return {
        "leave_type": leave_type.pk,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "half_day": half_day,
    }


class TestLeaveTypes:
    def test_everyone_can_read_leave_types(self, auth_client, api_client, leave_org):
        auth_client(leave_org.org.employee_user)

        response = api_client.get(LEAVE_TYPES)

        assert response.status_code == 200
        names = {row["name"] for row in response.data["results"]}
        assert names == {"Annual", "Sick", "Unpaid"}
        annual = next(
            row for row in response.data["results"] if row["name"] == "Annual"
        )
        assert annual["annual_days"] == 20.0

    def test_hr_can_create_a_type(self, auth_client, api_write, leave_org):
        auth_client(leave_org.org.hr)

        response = api_write(
            "post",
            LEAVE_TYPES,
            {"name": "Study", "annual_days": 5, "carry_over_max": 0},
        )

        assert response.status_code == 201
        assert response.data["name"] == "Study"
        assert response.data["annual_days"] == 5.0

    @pytest.mark.parametrize("role", ["manager", "employee"])
    def test_non_hr_cannot_create_a_type(
        self, auth_client, api_write, leave_org, role
    ):
        user = (
            leave_org.org.manager_user
            if role == "manager"
            else leave_org.org.employee_user
        )
        auth_client(user)

        response = api_write("post", LEAVE_TYPES, {"name": "Study"})

        assert response.status_code == 403

    def test_hr_can_update_and_delete_an_unused_type(
        self, auth_client, api_write, leave_org
    ):
        auth_client(leave_org.org.hr)

        created = api_write("post", LEAVE_TYPES, {"name": "Study", "annual_days": 5})
        assert created.status_code == 201, created.data
        updated = api_write(
            "patch", f"{LEAVE_TYPES}{created.data['id']}/", {"annual_days": 7}
        )
        deleted = api_write("delete", f"{LEAVE_TYPES}{created.data['id']}/")

        assert updated.status_code == 200
        assert updated.data["annual_days"] == 7.0
        assert deleted.status_code == 204

    def test_a_type_with_requests_cannot_be_deleted(
        self, auth_client, api_write, leave_org
    ):
        leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.hr)

        response = api_write("delete", f"{LEAVE_TYPES}{leave_org.types.annual.pk}/")

        assert response.status_code == 400
        assert "requests" in response.data["detail"]

    def test_logged_out_is_rejected(self, api_client):
        assert api_client.get(LEAVE_TYPES).status_code in (401, 403)


class TestBalances:
    def test_an_employee_sees_only_their_own_balances(
        self, auth_client, api_client, leave_org
    ):
        auth_client(leave_org.org.employee_user)

        response = api_client.get(BALANCES)

        assert response.status_code == 200
        assert response.data["count"] == 3
        assert {row["employee"] for row in response.data["results"]} == {
            leave_org.org.esha.pk
        }
        annual = next(
            row for row in response.data["results"] if row["leave_type_name"] == "Annual"
        )
        assert annual["allocated"] == 20.0
        assert annual["remaining"] == 20.0

    def test_hr_sees_every_balance(self, auth_client, api_client, leave_org):
        auth_client(leave_org.org.hr)

        response = api_client.get(BALANCES)

        assert response.data["count"] == 9

    def test_a_manager_sees_only_their_own_balances(
        self, auth_client, api_client, leave_org
    ):
        auth_client(leave_org.org.manager_user)

        response = api_client.get(BALANCES)

        assert response.data["count"] == 3
        assert {row["employee"] for row in response.data["results"]} == {
            leave_org.org.meera.pk
        }

    def test_year_filter(self, auth_client, api_client, leave_org):
        LeaveBalance.objects.create(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            year=2025,
            allocated=Decimal("20"),
        )
        auth_client(leave_org.org.employee_user)

        response = api_client.get(f"{BALANCES}?year=2025")

        assert response.data["count"] == 1
        assert response.data["results"][0]["year"] == 2025

    def test_invalid_year_is_rejected(self, auth_client, api_client, leave_org):
        auth_client(leave_org.org.employee_user)

        response = api_client.get(f"{BALANCES}?year=nope")

        assert response.status_code == 400
        assert "year" in response.data["fields"]

    def test_hr_can_filter_balances_by_employee(
        self, auth_client, api_client, leave_org
    ):
        auth_client(leave_org.org.hr)

        response = api_client.get(
            f"{BALANCES}?year=2026&employee={leave_org.org.esha.pk}"
        )

        assert response.data["count"] == 3
        assert {row["employee"] for row in response.data["results"]} == {
            leave_org.org.esha.pk
        }

    def test_an_employee_cannot_peek_through_the_employee_filter(
        self, auth_client, api_client, leave_org
    ):
        auth_client(leave_org.org.employee_user)

        other = api_client.get(f"{BALANCES}?employee={leave_org.org.meera.pk}")
        own = api_client.get(f"{BALANCES}?employee={leave_org.org.esha.pk}")

        # The scope is applied first, so the filter can narrow but never widen.
        assert other.data["count"] == 0
        assert own.data["count"] == 3
        assert {row["employee"] for row in own.data["results"]} == {
            leave_org.org.esha.pk
        }

    def test_balances_cannot_be_written(self, auth_client, api_write, leave_org):
        balance = LeaveBalance.objects.filter(employee=leave_org.org.esha).first()
        auth_client(leave_org.org.hr)

        response = api_write(
            "patch", f"{BALANCES}{balance.pk}/", {"allocated": 100}
        )

        assert response.status_code == 405


class TestCreateRequest:
    def test_an_employee_requests_leave_for_themselves(
        self, auth_client, api_write, leave_org
    ):
        auth_client(leave_org.org.employee_user)

        response = api_write(
            "post", REQUESTS, create_payload(leave_org.types.annual)
        )

        assert response.status_code == 201
        assert response.data["employee"] == leave_org.org.esha.pk
        assert response.data["employee_name"] == "Esha Employee"
        assert response.data["status"] == "pending"
        assert response.data["days"] == 4.0
        assert response.data["reviewer"] is None

    def test_a_half_day_is_half_a_day(self, auth_client, api_write, leave_org):
        auth_client(leave_org.org.employee_user)

        response = api_write(
            "post",
            REQUESTS,
            create_payload(
                leave_org.types.annual, start=TUESDAY, end=TUESDAY, half_day=True
            ),
        )

        assert response.status_code == 201
        assert response.data["days"] == 0.5

    def test_the_employee_field_cannot_be_spoofed(
        self, auth_client, api_write, leave_org
    ):
        auth_client(leave_org.org.employee_user)
        payload = create_payload(leave_org.types.annual) | {
            "employee": leave_org.org.meera.pk
        }

        response = api_write("post", REQUESTS, payload)

        assert response.status_code == 201
        assert response.data["employee"] == leave_org.org.esha.pk

    def test_an_overrun_is_rejected(self, auth_client, api_write, leave_org):
        LeaveBalance.objects.filter(
            employee=leave_org.org.esha, leave_type=leave_org.types.annual
        ).update(allocated=Decimal("2"))
        auth_client(leave_org.org.employee_user)

        response = api_write(
            "post", REQUESTS, create_payload(leave_org.types.annual)
        )

        assert response.status_code == 400
        assert "remaining" in response.data["detail"]

    def test_an_overlap_is_rejected(self, auth_client, api_write, leave_org):
        leave_request(
            leave_org.org.esha,
            leave_org.types.annual,
            start=MONDAY,
            end=FRIDAY,
        )
        auth_client(leave_org.org.employee_user)

        response = api_write(
            "post",
            REQUESTS,
            create_payload(leave_org.types.annual, start=THURSDAY, end=NEXT_MONDAY),
        )

        assert response.status_code == 400
        assert "overlap" in response.data["detail"]

    def test_an_end_before_start_is_a_field_error(
        self, auth_client, api_write, leave_org
    ):
        auth_client(leave_org.org.employee_user)

        response = api_write(
            "post",
            REQUESTS,
            create_payload(leave_org.types.annual, start=FRIDAY, end=MONDAY),
        )

        assert response.status_code == 400
        assert "end_date" in response.data["fields"]

    def test_a_weekend_only_request_is_rejected(
        self, auth_client, api_write, leave_org
    ):
        auth_client(leave_org.org.employee_user)

        response = api_write(
            "post",
            REQUESTS,
            create_payload(
                leave_org.types.annual,
                start=date(2026, 5, 9),
                end=date(2026, 5, 10),
            ),
        )

        assert response.status_code == 400
        assert "working days" in response.data["detail"]

    def test_an_account_without_an_employee_record_gets_a_clear_error(
        self, auth_client, api_write, leave_org
    ):
        auth_client(leave_org.org.hr)

        response = api_write(
            "post", REQUESTS, create_payload(leave_org.types.annual)
        )

        assert response.status_code == 400
        assert "employee record" in response.data["detail"]

    def test_logged_out_is_rejected(self, api_client):
        assert api_client.post(REQUESTS, {}, format="json").status_code in (401, 403)


class TestListRequests:
    def test_an_employee_sees_only_their_own(
        self, auth_client, api_client, leave_org
    ):
        leave_request(leave_org.org.esha, leave_org.types.annual)
        leave_request(leave_org.org.sam, leave_org.types.annual)
        auth_client(leave_org.org.employee_user)

        response = api_client.get(REQUESTS)

        assert response.data["count"] == 1
        assert response.data["results"][0]["employee"] == leave_org.org.esha.pk

    def test_a_manager_sees_their_team_and_themselves(
        self, auth_client, api_client, leave_org
    ):
        leave_request(leave_org.org.esha, leave_org.types.annual)
        leave_request(leave_org.org.meera, leave_org.types.sick)
        leave_request(leave_org.org.sam, leave_org.types.annual)
        auth_client(leave_org.org.manager_user)

        response = api_client.get(REQUESTS)

        assert response.data["count"] == 2
        assert {row["employee"] for row in response.data["results"]} == {
            leave_org.org.esha.pk,
            leave_org.org.meera.pk,
        }

    def test_hr_sees_everything(self, auth_client, api_client, leave_org):
        leave_request(leave_org.org.esha, leave_org.types.annual)
        leave_request(leave_org.org.sam, leave_org.types.annual)
        auth_client(leave_org.org.hr)

        response = api_client.get(REQUESTS)

        assert response.data["count"] == 2

    def test_filters_and_envelope(self, auth_client, api_client, leave_org):
        leave_request(leave_org.org.esha, leave_org.types.annual)
        approved = leave_request(
            leave_org.org.esha,
            leave_org.types.sick,
            start=THURSDAY,
            end=FRIDAY,
            status=LeaveRequest.Status.APPROVED,
        )
        leave_request(leave_org.org.sam, leave_org.types.annual)
        auth_client(leave_org.org.hr)

        pending_response = api_client.get(f"{REQUESTS}?status=pending")
        sick_response = api_client.get(
            f"{REQUESTS}?leave_type={leave_org.types.sick.pk}"
        )
        employee_response = api_client.get(
            f"{REQUESTS}?employee={leave_org.org.sam.pk}"
        )
        bad_status = api_client.get(f"{REQUESTS}?status=holiday")

        assert pending_response.data["count"] == 2
        assert sick_response.data["count"] == 1
        assert sick_response.data["results"][0]["id"] == approved.pk
        assert employee_response.data["count"] == 1
        assert bad_status.status_code == 400
        assert set(pending_response.data) >= {"count", "page", "pages", "results"}

    def test_mine_returns_only_the_callers_requests(
        self, auth_client, api_client, leave_org
    ):
        leave_request(leave_org.org.esha, leave_org.types.annual)
        leave_request(leave_org.org.meera, leave_org.types.sick)
        auth_client(leave_org.org.manager_user)

        response = api_client.get(f"{REQUESTS}?mine=true")

        assert response.data["count"] == 1
        assert response.data["results"][0]["employee"] == leave_org.org.meera.pk

    def test_mine_is_empty_without_an_employee_record(
        self, auth_client, api_client, leave_org
    ):
        leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.hr)

        response = api_client.get(f"{REQUESTS}?mine=true")

        assert response.data["count"] == 0

    def test_mine_rejects_a_non_boolean_value(
        self, auth_client, api_client, leave_org
    ):
        auth_client(leave_org.org.employee_user)

        response = api_client.get(f"{REQUESTS}?mine=yes")

        assert response.status_code == 400
        assert "mine" in response.data["fields"]

    def test_an_out_of_scope_request_is_404(self, auth_client, api_client, leave_org):
        hidden = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.sales_user)

        response = api_client.get(f"{REQUESTS}{hidden.pk}/")

        assert response.status_code == 404

    def test_delete_is_not_allowed(self, auth_client, api_write, leave_org):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.employee_user)

        response = api_write("delete", f"{REQUESTS}{request.pk}/")

        assert response.status_code == 405
        assert "cancelled" in response.data["detail"]


class TestReview:
    def test_a_manager_approves_a_team_request(
        self, auth_client, api_write, leave_org
    ):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.manager_user)

        response = api_write(
            "post", f"{REQUESTS}{request.pk}/approve/", {"comment": "Enjoy"}
        )

        assert response.status_code == 200
        assert response.data["status"] == "approved"
        assert response.data["reviewer_name"] == "Meera Manager"
        assert response.data["review_comment"] == "Enjoy"
        balance = LeaveBalance.objects.get(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            year=2026,
        )
        assert balance.used == Decimal("2")

    def test_an_employee_cannot_approve(self, auth_client, api_write, leave_org):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.employee_user)

        response = api_write("post", f"{REQUESTS}{request.pk}/approve/", {})

        assert response.status_code == 403

    def test_a_manager_cannot_approve_another_team(
        self, auth_client, api_write, leave_org
    ):
        request = leave_request(leave_org.org.sam, leave_org.types.annual)
        auth_client(leave_org.org.manager_user)

        response = api_write("post", f"{REQUESTS}{request.pk}/approve/", {})

        assert response.status_code == 404

    def test_hr_can_approve_anyone(self, auth_client, api_write, leave_org):
        request = leave_request(leave_org.org.sam, leave_org.types.annual)
        auth_client(leave_org.org.hr)

        response = api_write("post", f"{REQUESTS}{request.pk}/approve/", {})

        assert response.status_code == 200
        assert response.data["reviewer"] is None

    def test_approving_twice_is_a_clear_400(
        self, auth_client, api_write, leave_org
    ):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.manager_user)
        api_write("post", f"{REQUESTS}{request.pk}/approve/", {})

        response = api_write("post", f"{REQUESTS}{request.pk}/approve/", {})

        assert response.status_code == 400
        assert "already approved" in response.data["detail"]

    def test_rejecting_requires_a_comment(self, auth_client, api_write, leave_org):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.manager_user)

        response = api_write("post", f"{REQUESTS}{request.pk}/reject/", {})

        assert response.status_code == 400
        assert "comment" in response.data["fields"]

    def test_a_rejection_keeps_the_balance(self, auth_client, api_write, leave_org):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.manager_user)

        response = api_write(
            "post",
            f"{REQUESTS}{request.pk}/reject/",
            {"comment": "Team offsite"},
        )

        assert response.status_code == 200
        assert response.data["status"] == "rejected"
        balance = LeaveBalance.objects.get(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            year=2026,
        )
        assert balance.used == Decimal("0")

    def test_admin_can_review(self, auth_client, api_write, leave_org):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.admin)

        response = api_write("post", f"{REQUESTS}{request.pk}/approve/", {})

        assert response.status_code == 200


class TestCancel:
    def test_the_owner_cancels_a_pending_request(
        self, auth_client, api_write, leave_org
    ):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.employee_user)

        response = api_write("post", f"{REQUESTS}{request.pk}/cancel/", {})

        assert response.status_code == 200
        assert response.data["status"] == "cancelled"

    def test_cancelling_an_approved_request_restores_the_balance(
        self, auth_client, api_write, leave_org
    ):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.manager_user)
        api_write("post", f"{REQUESTS}{request.pk}/approve/", {})
        auth_client(leave_org.org.employee_user)

        response = api_write("post", f"{REQUESTS}{request.pk}/cancel/", {})

        assert response.status_code == 200
        balance = LeaveBalance.objects.get(
            employee=leave_org.org.esha,
            leave_type=leave_org.types.annual,
            year=2026,
        )
        assert balance.used == Decimal("0")

    def test_a_manager_cannot_cancel_someone_elses_request(
        self, auth_client, api_write, leave_org
    ):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.manager_user)

        response = api_write("post", f"{REQUESTS}{request.pk}/cancel/", {})

        assert response.status_code == 403

    def test_hr_cannot_cancel_someone_elses_request(
        self, auth_client, api_write, leave_org
    ):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.hr)

        response = api_write("post", f"{REQUESTS}{request.pk}/cancel/", {})

        assert response.status_code == 403

    def test_admin_can_cancel(self, auth_client, api_write, leave_org):
        request = leave_request(leave_org.org.esha, leave_org.types.annual)
        auth_client(leave_org.org.admin)

        response = api_write("post", f"{REQUESTS}{request.pk}/cancel/", {})

        assert response.status_code == 200
        assert response.data["status"] == "cancelled"

    def test_a_rejected_request_cannot_be_cancelled(
        self, auth_client, api_write, leave_org
    ):
        request = leave_request(
            leave_org.org.esha,
            leave_org.types.annual,
            status=LeaveRequest.Status.REJECTED,
        )
        auth_client(leave_org.org.employee_user)

        response = api_write("post", f"{REQUESTS}{request.pk}/cancel/", {})

        assert response.status_code == 400
        assert "cancelled" in response.data["detail"]


class TestPreview:
    def test_preview_returns_days_and_balance(
        self, auth_client, api_write, leave_org
    ):
        auth_client(leave_org.org.employee_user)

        response = api_write(
            "post", f"{REQUESTS}preview/", create_payload(leave_org.types.annual)
        )

        assert response.status_code == 200
        assert response.data["days"] == 4.0
        assert response.data["remaining"] == 20.0
        assert response.data["sufficient"] is True
        assert response.data["overlap"] is False

    def test_preview_flags_an_insufficient_balance(
        self, auth_client, api_write, leave_org
    ):
        LeaveBalance.objects.filter(
            employee=leave_org.org.esha, leave_type=leave_org.types.annual
        ).update(allocated=Decimal("2"))
        auth_client(leave_org.org.employee_user)

        response = api_write(
            "post", f"{REQUESTS}preview/", create_payload(leave_org.types.annual)
        )

        assert response.data["sufficient"] is False

    def test_preview_flags_an_overlap(self, auth_client, api_write, leave_org):
        leave_request(
            leave_org.org.esha, leave_org.types.annual, start=MONDAY, end=FRIDAY
        )
        auth_client(leave_org.org.employee_user)

        response = api_write(
            "post",
            f"{REQUESTS}preview/",
            create_payload(leave_org.types.annual, start=THURSDAY, end=NEXT_MONDAY),
        )

        assert response.data["overlap"] is True


class TestCalendar:
    def test_an_employee_sees_their_team_not_other_teams(
        self, auth_client, api_client, leave_org
    ):
        leave_request(
            leave_org.org.meera,
            leave_org.types.annual,
            status=LeaveRequest.Status.APPROVED,
        )
        leave_request(
            leave_org.org.sam,
            leave_org.types.annual,
            status=LeaveRequest.Status.APPROVED,
        )
        leave_request(leave_org.org.esha, leave_org.types.annual)  # pending
        auth_client(leave_org.org.employee_user)

        response = api_client.get(f"{CALENDAR}?year=2026&month=5")

        assert response.status_code == 200
        assert [row["employee_name"] for row in response.data["results"]] == [
            "Meera Manager"
        ]
        assert [row["name"] for row in response.data["holidays"]] == ["Founders Day"]

    def test_a_manager_sees_their_team(self, auth_client, api_client, leave_org):
        leave_request(
            leave_org.org.meera,
            leave_org.types.sick,
            status=LeaveRequest.Status.APPROVED,
        )
        leave_request(
            leave_org.org.esha,
            leave_org.types.annual,
            start=THURSDAY,
            end=FRIDAY,
            status=LeaveRequest.Status.APPROVED,
        )
        leave_request(
            leave_org.org.sam,
            leave_org.types.annual,
            status=LeaveRequest.Status.APPROVED,
        )
        auth_client(leave_org.org.manager_user)

        response = api_client.get(f"{CALENDAR}?year=2026&month=5")

        assert {row["employee_name"] for row in response.data["results"]} == {
            "Meera Manager",
            "Esha Employee",
        }
        assert response.data["year"] == 2026
        assert response.data["month"] == 5

    def test_hr_sees_everyone(self, auth_client, api_client, leave_org):
        leave_request(
            leave_org.org.meera,
            leave_org.types.annual,
            status=LeaveRequest.Status.APPROVED,
        )
        leave_request(
            leave_org.org.sam,
            leave_org.types.annual,
            status=LeaveRequest.Status.APPROVED,
        )
        auth_client(leave_org.org.hr)

        response = api_client.get(f"{CALENDAR}?year=2026&month=5")

        assert response.data["results"].__len__() == 2

    def test_an_employee_sees_their_own_leave_any_month(
        self, auth_client, api_client, leave_org
    ):
        leave_request(
            leave_org.org.esha,
            leave_org.types.annual,
            start=date(2026, 6, 1),
            end=date(2026, 6, 1),
            status=LeaveRequest.Status.APPROVED,
            days=Decimal("1"),
        )
        auth_client(leave_org.org.employee_user)

        may = api_client.get(f"{CALENDAR}?year=2026&month=5")
        june = api_client.get(f"{CALENDAR}?year=2026&month=6")

        assert may.data["results"] == []
        assert [row["employee_name"] for row in june.data["results"]] == [
            "Esha Employee"
        ]

    def test_invalid_month_is_rejected(self, auth_client, api_client, leave_org):
        auth_client(leave_org.org.employee_user)

        response = api_client.get(f"{CALENDAR}?year=2026&month=13")

        assert response.status_code == 400
        assert "month" in response.data["fields"]

    def test_logged_out_is_rejected(self, api_client):
        assert api_client.get(CALENDAR).status_code in (401, 403)


class TestAuditAttribution:
    def test_leave_type_changes_are_audited(
        self, auth_client, api_write, leave_org
    ):
        auth_client(leave_org.org.hr)

        created = api_write("post", LEAVE_TYPES, {"name": "Study", "annual_days": 5})
        api_write("patch", f"{LEAVE_TYPES}{created.data['id']}/", {"annual_days": 7})

        rows = AuditLog.objects.filter(
            model="timeoff.leavetype", object_id=str(created.data["id"])
        ).order_by("created_at", "id")
        assert [row.action for row in rows] == ["create", "update"]
        assert all(row.actor == leave_org.org.hr for row in rows)

    def test_create_and_review_carry_the_actor(
        self, auth_client, api_write, leave_org
    ):
        auth_client(leave_org.org.employee_user)
        created = api_write("post", REQUESTS, create_payload(leave_org.types.annual))
        request_id = created.data["id"]

        auth_client(leave_org.org.manager_user)
        api_write("post", f"{REQUESTS}{request_id}/approve/", {})

        rows = AuditLog.objects.filter(
            model="timeoff.leaverequest", object_id=str(request_id)
        ).order_by("created_at")
        assert [row.action for row in rows] == ["create", "update"]
        assert rows[0].actor == leave_org.org.employee_user
        assert rows[1].actor == leave_org.org.manager_user
