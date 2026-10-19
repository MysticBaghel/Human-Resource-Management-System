"""Audit log API, coverage and integrity tests."""

import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.employees.models import EmployeeInvite
from apps.organization.models import Team
from apps.timeoff.models import LeaveRequest

AUDIT = "/api/v1/audit-logs/"
EMPLOYEES = "/api/v1/employees/"
TEAMS = "/api/v1/teams/"
REQUESTS = "/api/v1/leave-requests/"


def create_employee(api_write, email="audit.person@example.com", **extra):
    payload = {
        "email": email,
        "first_name": "Audit",
        "last_name": "Person",
        "start_date": "2025-01-06",
        **extra,
    }
    return api_write("post", EMPLOYEES, payload)


def create_team(api_write, name="Audit Team"):
    return api_write("post", TEAMS, {"name": name})


class TestAccess:
    def test_hr_and_admin_can_read(self, auth_client, api_client, make_user):
        for role in ("hr", "admin"):
            user = make_user(f"{role}-audit@example.com", role=role)
            auth_client(user)
            response = api_client.get(AUDIT)
            assert response.status_code == 200, role

    @pytest.mark.parametrize("role", ["manager", "employee"])
    def test_other_roles_are_forbidden(
        self, auth_client, api_client, make_user, role
    ):
        auth_client(make_user(f"{role}-audit@example.com", role=role))

        response = api_client.get(AUDIT)

        assert response.status_code == 403

    def test_logged_out_is_forbidden(self, api_client):
        assert api_client.get(AUDIT).status_code in (401, 403)

    def test_detail_follows_the_same_rule(
        self, auth_client, api_client, api_write, make_user
    ):
        hr = make_user("detail-hr@example.com", role="hr")
        manager = make_user("detail-manager@example.com", role="manager")
        auth_client(hr)
        create_team(api_write, "Detail Team")
        row = AuditLog.objects.get(model="organization.team")
        auth_client(manager)

        detail = api_client.get(f"{AUDIT}{row.pk}/")

        assert detail.status_code == 403

    def test_missing_row_is_404_for_hr(self, auth_client, api_client, make_user):
        auth_client(make_user("missing-hr@example.com", role="hr"))

        assert api_client.get(f"{AUDIT}999999/").status_code == 404

    def test_audit_rows_cannot_be_changed_or_deleted(
        self, auth_client, api_client, api_write, make_user
    ):
        auth_client(make_user("readonly-hr@example.com", role="hr"))
        create_team(api_write, "Read Only Team")
        row = AuditLog.objects.get(model="organization.team")

        patch = api_write("patch", f"{AUDIT}{row.pk}/", {"action": "delete"})
        delete = api_write("delete", f"{AUDIT}{row.pk}/")
        post = api_write("post", AUDIT, {})

        assert patch.status_code == 405
        assert delete.status_code == 405
        assert post.status_code == 405
        row.refresh_from_db()
        assert row.action == "create"


class TestSerialization:
    def test_row_contains_labels_summary_and_actor(
        self, auth_client, api_client, api_write, make_user
    ):
        hr = make_user("labels-hr@example.com", role="hr")
        auth_client(hr)
        created = create_employee(api_write, email="labels.person@example.com")

        response = api_client.get(
            f"{AUDIT}?model=employees.employee&action=create"
        )
        row = next(
            item
            for item in response.data["results"]
            if item["object_id"] == str(created.data["id"])
        )

        assert row["actor"] == hr.pk
        assert row["actor_email"] == hr.email
        assert row["actor_label"] == hr.email
        assert row["action"] == "create"
        assert row["action_label"] == "Create"
        assert row["model"] == "employees.employee"
        assert row["model_label"] == "Employee"
        assert row["summary"] == (
            f"Created employee #{created.data['id']} (Audit Person)"
        )
        assert row["changes"]["after"]["first_name"] == "Audit"

    def test_rows_without_an_actor_are_labelled_system(
        self, auth_client, api_client, make_user
    ):
        # A direct ORM write has no request/actor, like a management command.
        Team.objects.create(name="System Team")
        auth_client(make_user("system-hr@example.com", role="hr"))

        response = api_client.get(f"{AUDIT}?model=organization.team")
        row = response.data["results"][0]

        assert row["actor"] is None
        assert row["actor_email"] is None
        assert row["actor_label"] == "System"

    def test_invite_acceptance_is_audited_without_the_token(
        self, auth_client, api_write, make_user
    ):
        hr = make_user("invite-hr@example.com", role="hr")
        auth_client(hr)
        create_employee(api_write, email="invited@example.com")
        invite = EmployeeInvite.objects.get(user__email="invited@example.com")

        accepted = api_write(
            "post",
            "/api/v1/auth/accept-invite/",
            {"token": str(invite.token), "password": "BrandNewPass!42"},
        )

        assert accepted.status_code == 200
        rows = AuditLog.objects.filter(model="employees.employeeinvite")
        assert rows.count() == 1
        row = rows.get()
        assert row.actor.email == "invited@example.com"
        data = AuditLogSerializer(row).data
        assert data["summary"] == f"Accepted employee invite #{invite.pk}"
        assert "accepted_at" in data["changes"]
        serialized = json.dumps(data)
        assert "password" not in serialized.lower()
        assert "token" not in serialized.lower()
        assert str(invite.token) not in serialized


class TestFilters:
    def _setup(self, auth_client, api_write, make_user):
        hr = make_user("filters-hr@example.com", role="hr")
        auth_client(hr)
        employee = create_employee(api_write, email="filters.person@example.com")
        api_write(
            "patch",
            f"{EMPLOYEES}{employee.data['id']}/",
            {"job_title": "QA"},
        )
        team = create_team(api_write, "Filter Team")
        return hr, employee.data, team.data

    def test_action_model_actor_and_count(
        self, auth_client, api_client, api_write, make_user
    ):
        hr, employee, team = self._setup(auth_client, api_write, make_user)

        everything = api_client.get(AUDIT)
        creates = api_client.get(f"{AUDIT}?action=create")
        updates = api_client.get(f"{AUDIT}?action=update")
        teams = api_client.get(f"{AUDIT}?model=organization.team")
        actors = api_client.get(f"{AUDIT}?actor={hr.pk}")

        assert everything.data["count"] == 3
        assert creates.data["count"] == 2
        assert updates.data["count"] == 1
        assert [row["model"] for row in teams.data["results"]] == [
            "organization.team"
        ]
        assert actors.data["count"] == 3
        assert everything.data["results"][0]["model"] == "organization.team"

    def test_search_and_date_range(
        self, auth_client, api_client, api_write, make_user
    ):
        self._setup(auth_client, api_write, make_user)
        today = timezone.localdate().isoformat()
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()

        by_actor = api_client.get(f"{AUDIT}?search=filters-hr@example.com")
        today_rows = api_client.get(
            f"{AUDIT}?date_from={today}&date_to={today}"
        )
        future_rows = api_client.get(f"{AUDIT}?date_from={tomorrow}")

        assert by_actor.data["count"] == 3
        assert today_rows.data["count"] == 3
        assert future_rows.data["count"] == 0

    def test_pagination(self, auth_client, api_client, make_user):
        auth_client(make_user("pages-hr@example.com", role="hr"))
        for index in range(21):
            Team.objects.create(name=f"Paged Team {index}")

        first = api_client.get(AUDIT)
        second = api_client.get(f"{AUDIT}?page=2")

        assert first.data["count"] == 21
        assert first.data["pages"] == 2
        assert len(first.data["results"]) == 20
        assert len(second.data["results"]) == 1
        assert set(first.data) >= {"count", "page", "pages", "page_size", "results"}

    @pytest.mark.parametrize(
        "query,field",
        [
            ("?action=nope", "action"),
            ("?model=nope", "model"),
            ("?actor=abc", "actor"),
            ("?date_from=2026-13-01", "date_from"),
            ("?date_to=2026-13-01", "date_to"),
            ("?date_from=2026-05-02&date_to=2026-05-01", "date_to"),
        ],
    )
    def test_invalid_filters_are_field_errors(
        self, auth_client, api_client, make_user, query, field
    ):
        auth_client(make_user("invalid-hr@example.com", role="hr"))

        response = api_client.get(f"{AUDIT}{query}")

        assert response.status_code == 400
        assert field in response.data["fields"]

    def test_actor_choices_only_include_real_actors(
        self, auth_client, api_client, api_write, make_user
    ):
        hr = make_user("choices-hr@example.com", role="hr")
        admin = make_user("choices-admin@example.com", role="admin")
        auth_client(hr)
        create_team(api_write, "Choices Team")
        auth_client(admin)
        create_team(api_write, "Choices Team Admin")
        auth_client(hr)

        response = api_client.get(f"{AUDIT}actors/")

        assert response.status_code == 200
        emails = {row["email"] for row in response.data}
        assert emails == {hr.email, admin.email}


class TestAuditCoverage:
    def test_balance_changes_are_folded_into_the_request_rows(
        self, auth_client, api_write, leave_org
    ):
        org = leave_org.org
        auth_client(org.employee_user)
        created = api_write(
            "post",
            REQUESTS,
            {
                "leave_type": leave_org.types.annual.pk,
                "start_date": "2026-05-04",
                "end_date": "2026-05-05",
            },
        )
        request_id = created.data["id"]

        auth_client(org.manager_user)
        api_write(
            "post",
            f"{REQUESTS}{request_id}/approve/",
            {"comment": "Approved"},
        )

        approve_row = AuditLog.objects.get(
            model="timeoff.leaverequest",
            object_id=str(request_id),
            action="update",
        )
        changes = approve_row.changes["changes"]
        assert changes["status"] == {
            "before": "pending",
            "after": "approved",
        }
        assert "reviewed_at" in changes
        assert Decimal(changes["balance_used"]["before"]) == Decimal("0")
        assert Decimal(changes["balance_used"]["after"]) == Decimal(
            str(created.data["days"])
        )

        auth_client(org.employee_user)
        api_write("post", f"{REQUESTS}{request_id}/cancel/", {})

        updates = AuditLog.objects.filter(
            model="timeoff.leaverequest",
            object_id=str(request_id),
            action="update",
        ).order_by("id")
        assert updates.count() == 2  # approve, then cancel: no duplicates
        cancel_changes = updates.last().changes["changes"]
        assert cancel_changes["balance_used"]["before"] == (
            approve_row.changes["changes"]["balance_used"]["after"]
        )
        assert Decimal(cancel_changes["balance_used"]["after"]) == Decimal("0")

    def test_create_and_update_write_one_row_each(
        self, auth_client, api_write, make_user
    ):
        auth_client(make_user("once-hr@example.com", role="hr"))
        employee = create_employee(api_write, email="once.person@example.com")
        api_write(
            "patch",
            f"{EMPLOYEES}{employee.data['id']}/",
            {"job_title": "Staff QA"},
        )

        rows = AuditLog.objects.filter(
            model="employees.employee", object_id=str(employee.data["id"])
        )
        assert rows.filter(action="create").count() == 1
        assert rows.filter(action="update").count() == 1

    def test_failed_transaction_leaves_no_audit_row(self, db):
        baseline = AuditLog.objects.count()

        with pytest.raises(RuntimeError):
            with transaction.atomic():
                Team.objects.create(name="Rollback Team")
                raise RuntimeError("force rollback")

        assert AuditLog.objects.count() == baseline
        assert not Team.objects.filter(name="Rollback Team").exists()

    def test_no_sensitive_keys_anywhere_in_audit_json(
        self, auth_client, api_write, make_user
    ):
        hr = make_user("secrets-hr@example.com", role="hr")
        auth_client(hr)
        create_employee(api_write, email="secrets.person@example.com")
        invite = EmployeeInvite.objects.get(user__email="secrets.person@example.com")
        api_write(
            "post",
            "/api/v1/auth/accept-invite/",
            {"token": str(invite.token), "password": "BrandNewPass!42"},
        )

        dump = json.dumps(list(AuditLog.objects.values("changes"))).lower()
        for forbidden in ("password", "token", "sessionid", "csrf", "secret"):
            assert forbidden not in dump

    def test_manager_and_employee_filters_cannot_bypass_permissions(
        self, auth_client, api_client, make_user
    ):
        for role in ("manager", "employee"):
            auth_client(make_user(f"{role}-bypass@example.com", role=role))
            response = api_client.get(
                f"{AUDIT}?action=create&actor=1&date_from=2020-01-01"
            )
            assert response.status_code == 403
