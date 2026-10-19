"""Dashboard tests: metrics, scoping and empty states for every role."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.timeoff.models import LeaveRequest

DASHBOARD = "/api/v1/dashboard/"


def make_leave(
    employee,
    leave_type,
    *,
    status=LeaveRequest.Status.PENDING,
    start=None,
    end=None,
    days="1",
    reviewed_at=None,
):
    today = timezone.localdate()
    return LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=start or today,
        end_date=end or start or today,
        days=days,
        status=status,
        reviewed_at=reviewed_at,
    )


class TestAdminDashboard:
    def test_company_metrics(self, auth_client, api_client, leave_org):
        org = leave_org.org
        today = timezone.localdate()
        make_leave(
            org.esha,
            leave_org.types.annual,
            start=today + timedelta(days=1),
            end=today + timedelta(days=1),
        )
        make_leave(
            org.esha,
            leave_org.types.sick,
            status=LeaveRequest.Status.APPROVED,
        )
        auth_client(org.admin)

        response = api_client.get(DASHBOARD)

        assert response.status_code == 200
        assert response.data["role"] == "admin"
        metrics = response.data["metrics"]
        assert metrics == {
            "active_employees": 3,
            "teams": 2,
            "pending_leave_requests": 1,
            "on_leave_today": 1,
        }
        assert response.data["recent_activity"]
        assert "balances" not in response.data

    def test_deactivated_employees_are_not_active(
        self, auth_client, api_client, leave_org
    ):
        org = leave_org.org
        org.sam.status = "inactive"
        org.sam.save(update_fields=["status"])
        auth_client(org.admin)

        response = api_client.get(DASHBOARD)

        assert response.data["metrics"]["active_employees"] == 2

    def test_empty_company(self, auth_client, api_client, make_user):
        auth_client(make_user("lonely-admin@example.com", role="admin"))

        response = api_client.get(DASHBOARD)

        assert response.status_code == 200
        assert response.data["metrics"] == {
            "active_employees": 0,
            "teams": 0,
            "pending_leave_requests": 0,
            "on_leave_today": 0,
        }
        assert response.data["recent_activity"] == []


class TestHRDashboard:
    def test_hr_metrics_and_hr_review_count(self, auth_client, api_client, leave_org):
        org = leave_org.org
        make_leave(org.esha, leave_org.types.annual)  # has a manager
        make_leave(org.sam, leave_org.types.annual)  # no manager -> HR reviews
        auth_client(org.hr)

        response = api_client.get(DASHBOARD)

        assert response.status_code == 200
        assert response.data["role"] == "hr"
        metrics = response.data["metrics"]
        assert metrics["active_employees"] == 3
        assert metrics["teams"] == 2
        assert metrics["pending_leave_requests"] == 2
        assert metrics["pending_without_manager"] == 1
        assert metrics["on_leave_today"] == 0
        assert isinstance(response.data["recent_employee_changes"], list)
        assert isinstance(response.data["recent_activity"], list)
        assert "balances" not in response.data


class TestManagerDashboard:
    def test_manager_sees_only_their_review_scope(
        self, auth_client, api_client, leave_org
    ):
        org = leave_org.org
        today = timezone.localdate()
        team_pending = make_leave(
            org.esha,
            leave_org.types.annual,
            start=today + timedelta(days=1),
            end=today + timedelta(days=1),
        )
        make_leave(org.meera, leave_org.types.sick)  # own request: not approvable
        make_leave(
            org.sam,
            leave_org.types.annual,
            start=today + timedelta(days=1),
            end=today + timedelta(days=1),
        )  # other team
        make_leave(
            org.esha,
            leave_org.types.sick,
            status=LeaveRequest.Status.APPROVED,
            start=today,
            end=today,
        )
        make_leave(
            org.sam,
            leave_org.types.sick,
            status=LeaveRequest.Status.APPROVED,
            start=today,
            end=today,
        )
        make_leave(
            org.esha,
            leave_org.types.annual,
            status=LeaveRequest.Status.APPROVED,
            start=today + timedelta(days=10),
            end=today + timedelta(days=11),
        )
        # Make the team's pending request look old enough to need attention.
        LeaveRequest.objects.filter(pk=team_pending.pk).update(
            created_at=timezone.now() - timedelta(days=3)
        )
        auth_client(org.manager_user)

        response = api_client.get(DASHBOARD)

        assert response.status_code == 200
        assert response.data["role"] == "manager"
        metrics = response.data["metrics"]
        assert metrics == {
            "team_employees": 2,
            "pending_leave_requests": 1,
            "pending_attention": 1,
            "on_leave_today": 1,
        }
        assert [row["id"] for row in response.data["pending_requests"]] == [
            team_pending.pk
        ]
        upcoming = response.data["upcoming_leave"]
        assert len(upcoming) == 1
        assert upcoming[0]["employee_name"] == "Esha Employee"

    def test_manager_without_an_employee_record_gets_zeros(
        self, auth_client, api_client, make_user
    ):
        auth_client(make_user("no-profile-manager@example.com", role="manager"))

        response = api_client.get(DASHBOARD)

        assert response.status_code == 200
        assert response.data["metrics"] == {
            "team_employees": 0,
            "pending_leave_requests": 0,
            "pending_attention": 0,
            "on_leave_today": 0,
        }
        assert response.data["pending_requests"] == []
        assert response.data["upcoming_leave"] == []


class TestEmployeeDashboard:
    def test_employee_sees_only_their_own_data(
        self, auth_client, api_client, leave_org
    ):
        org = leave_org.org
        today = timezone.localdate()
        own_pending = make_leave(org.esha, leave_org.types.annual)
        make_leave(org.sam, leave_org.types.annual)
        upcoming = make_leave(
            org.esha,
            leave_org.types.sick,
            status=LeaveRequest.Status.APPROVED,
            start=today + timedelta(days=7),
            end=today + timedelta(days=8),
        )
        decided = make_leave(
            org.esha,
            leave_org.types.annual,
            status=LeaveRequest.Status.APPROVED,
            start=today + timedelta(days=14),
            end=today + timedelta(days=15),
            reviewed_at=timezone.now(),
        )
        auth_client(org.employee_user)

        response = api_client.get(DASHBOARD)

        assert response.status_code == 200
        assert response.data["role"] == "employee"
        assert response.data["metrics"]["pending_leave_requests"] == 1
        assert response.data["metrics"]["upcoming_leave_count"] == 2
        assert len(response.data["balances"]) == 3
        assert [row["id"] for row in response.data["pending_requests"]] == [
            own_pending.pk
        ]
        assert [row["id"] for row in response.data["upcoming_leave"]] == [
            upcoming.pk,
            decided.pk,
        ]
        assert [row["id"] for row in response.data["recent_decisions"]] == [
            decided.pk
        ]
        # No company-wide fields for an employee.
        assert "active_employees" not in response.data["metrics"]
        assert "teams" not in response.data["metrics"]
        assert "recent_activity" not in response.data

    def test_employee_without_a_record_gets_an_empty_shell(
        self, auth_client, api_client, make_user
    ):
        auth_client(make_user("no-profile@example.com", role="employee"))

        response = api_client.get(DASHBOARD)

        assert response.status_code == 200
        assert response.data["metrics"] == {
            "pending_leave_requests": 0,
            "upcoming_leave_count": 0,
        }
        assert response.data["balances"] == []
        assert response.data["pending_requests"] == []
        assert response.data["upcoming_leave"] == []
        assert response.data["recent_decisions"] == []


class TestDashboardAccess:
    def test_logged_out_is_rejected(self, api_client):
        assert api_client.get(DASHBOARD).status_code in (401, 403)

    def test_only_get_is_allowed(self, auth_client, api_write, leave_org):
        auth_client(leave_org.org.employee_user)

        response = api_write("post", DASHBOARD, {})

        assert response.status_code == 405
