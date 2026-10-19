"""Employee endpoints: scoping, field rules, deactivation, filters and audit."""

import pytest

from apps.audit.models import AuditLog
from apps.accounts.models import User

LIST_URL = "/api/v1/employees/"
LOGIN_URL = "/api/v1/auth/login/"


def detail_url(employee) -> str:
    return f"{LIST_URL}{employee.pk}/"


def action_url(employee, action: str) -> str:
    return f"{detail_url(employee)}{action}/"


def new_employee_payload(team) -> dict:
    return {
        "email": "new.hire@example.com",
        "first_name": "New",
        "last_name": "Hire",
        "job_title": "Designer",
        "start_date": "2024-05-06",
        "team": team.pk,
        "role": "employee",
    }


class TestScoping:
    def test_hr_lists_everyone(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        response = api_client.get(LIST_URL)

        assert response.status_code == 200
        assert response.data["count"] == 3
        assert {row["email"] for row in response.data["results"]} == {
            "manager@example.com",
            "employee@example.com",
            "sales@example.com",
        }

    def test_admin_lists_everyone(self, auth_client, api_client, demo_org):
        auth_client(demo_org.admin)

        response = api_client.get(LIST_URL)

        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_manager_sees_own_team_and_self(self, auth_client, api_client, demo_org):
        auth_client(demo_org.manager_user)

        response = api_client.get(LIST_URL)

        assert response.status_code == 200
        assert {row["email"] for row in response.data["results"]} == {
            "manager@example.com",
            "employee@example.com",
        }

    def test_employee_sees_only_self(self, auth_client, api_client, demo_org):
        auth_client(demo_org.employee_user)

        response = api_client.get(LIST_URL)

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["email"] == "employee@example.com"

    def test_employee_cannot_read_another_record(
        self, auth_client, api_client, demo_org
    ):
        auth_client(demo_org.sales_user)

        response = api_client.get(detail_url(demo_org.esha))

        assert response.status_code == 404

    def test_manager_can_read_a_team_member(self, auth_client, api_client, demo_org):
        auth_client(demo_org.manager_user)

        response = api_client.get(detail_url(demo_org.esha))

        assert response.status_code == 200
        assert response.data["team_name"] == "Engineering"

    def test_manager_cannot_read_outside_own_team(
        self, auth_client, api_client, demo_org
    ):
        auth_client(demo_org.manager_user)

        response = api_client.get(detail_url(demo_org.sam))

        assert response.status_code == 404

    def test_hr_can_read_anyone(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        response = api_client.get(detail_url(demo_org.sam))

        assert response.status_code == 200

    def test_employee_can_read_own_record(self, auth_client, api_client, demo_org):
        auth_client(demo_org.employee_user)

        response = api_client.get(detail_url(demo_org.esha))

        assert response.status_code == 200
        assert response.data["full_name"] == "Esha Employee"

    def test_logged_out_is_rejected(self, api_client):
        response = api_client.get(LIST_URL)

        assert response.status_code in (401, 403)


class TestCreate:
    def test_hr_creates_an_employee_with_an_invite_and_one_audit_row(
        self, auth_client, api_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        response = api_write(
            "post", LIST_URL, new_employee_payload(demo_org.engineering)
        )

        assert response.status_code == 201
        assert response.data["email"] == "new.hire@example.com"
        assert response.data["role"] == "employee"
        assert response.data["status"] == "active"
        assert response.data["team_name"] == "Engineering"

        user = User.objects.get(email="new.hire@example.com")
        assert user.is_active is False
        assert not user.has_usable_password()

        rows = AuditLog.objects.filter(
            model="employees.employee", object_id=str(response.data["id"])
        )
        assert rows.count() == 1
        assert rows.get().actor == demo_org.hr

    def test_hr_cannot_grant_the_admin_role(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)
        payload = new_employee_payload(demo_org.engineering) | {"role": "admin"}

        response = api_write("post", LIST_URL, payload)

        assert response.status_code == 403
        assert not User.objects.filter(email="new.hire@example.com").exists()

    def test_admin_can_grant_the_admin_role(self, auth_client, api_write, demo_org):
        auth_client(demo_org.admin)
        payload = new_employee_payload(demo_org.engineering) | {"role": "admin"}

        response = api_write("post", LIST_URL, payload)

        assert response.status_code == 201
        assert response.data["role"] == "admin"
        assert User.objects.get(email="new.hire@example.com").role == "admin"

    @pytest.mark.parametrize("role", ["manager", "employee"])
    def test_non_hr_cannot_create(self, auth_client, api_write, demo_org, role):
        user = demo_org.manager_user if role == "manager" else demo_org.employee_user
        auth_client(user)

        response = api_write(
            "post", LIST_URL, new_employee_payload(demo_org.engineering)
        )

        assert response.status_code == 403

    def test_hr_can_create_a_manager(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)
        payload = new_employee_payload(demo_org.engineering) | {
            "email": "new.manager@example.com",
            "role": "manager",
        }

        response = api_write("post", LIST_URL, payload)

        assert response.status_code == 201
        assert response.data["role"] == "manager"

    def test_duplicate_email_is_a_field_error(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)
        payload = new_employee_payload(demo_org.engineering) | {
            "email": "employee@example.com"
        }

        response = api_write("post", LIST_URL, payload)

        assert response.status_code == 400
        assert "email" in response.data["fields"]

    def test_missing_required_fields_are_reported(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        response = api_write("post", LIST_URL, {})

        assert response.status_code == 400
        assert {"email", "first_name", "last_name", "start_date"} <= set(
            response.data["fields"]
        )


class TestUpdate:
    def test_employee_can_update_their_own_phone(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.employee_user)

        response = api_write(
            "patch", detail_url(demo_org.esha), {"phone": "+1 555 0199"}
        )

        assert response.status_code == 200
        assert response.data["phone"] == "+1 555 0199"

    def test_employee_cannot_update_their_other_fields(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.employee_user)

        response = api_write(
            "patch", detail_url(demo_org.esha), {"job_title": "Head of Everything"}
        )

        assert response.status_code == 403
        assert response.data["detail"] == (
            "Employees may only edit their own phone number."
        )
        demo_org.esha.refresh_from_db()
        assert demo_org.esha.job_title == "Software Engineer"

    def test_employee_cannot_mix_phone_with_other_fields(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.employee_user)

        response = api_write(
            "patch",
            detail_url(demo_org.esha),
            {"phone": "+1 555 0199", "job_title": "Head of Everything"},
        )

        assert response.status_code == 403

    def test_employee_cannot_update_another_employee(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.sales_user)

        response = api_write("patch", detail_url(demo_org.esha), {"phone": "x"})

        assert response.status_code == 404

    def test_manager_cannot_update_a_team_member(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.manager_user)

        response = api_write(
            "patch", detail_url(demo_org.esha), {"job_title": "Something"}
        )

        assert response.status_code == 403

    def test_hr_updates_any_field(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        response = api_write(
            "patch",
            detail_url(demo_org.esha),
            {
                "job_title": "Staff Engineer",
                "team": demo_org.sales.pk,
                "manager": None,
                "phone": "",
            },
        )

        assert response.status_code == 200
        assert response.data["job_title"] == "Staff Engineer"
        assert response.data["team_name"] == "Sales"
        assert response.data["manager"] is None
        assert response.data["manager_name"] is None

    def test_email_change_updates_the_login(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        response = api_write(
            "patch", detail_url(demo_org.esha), {"email": "esha.new@example.com"}
        )

        assert response.status_code == 200
        assert response.data["email"] == "esha.new@example.com"
        demo_org.employee_user.refresh_from_db()
        assert demo_org.employee_user.email == "esha.new@example.com"

    def test_email_change_to_an_existing_address_is_rejected(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        response = api_write(
            "patch", detail_url(demo_org.esha), {"email": "sales@example.com"}
        )

        assert response.status_code == 400
        assert "email" in response.data["fields"]

    def test_employee_cannot_be_their_own_manager(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        response = api_write(
            "patch", detail_url(demo_org.meera), {"manager": demo_org.meera.pk}
        )

        assert response.status_code == 400
        assert "manager" in response.data["fields"]

    def test_hr_can_change_a_role_but_not_to_admin(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        promoted = api_write(
            "patch", detail_url(demo_org.esha), {"role": "manager"}
        )
        to_admin = api_write(
            "patch", detail_url(demo_org.esha), {"role": "admin"}
        )

        assert promoted.status_code == 200
        assert promoted.data["role"] == "manager"
        assert to_admin.status_code == 403

    def test_delete_is_not_allowed(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        response = api_write("delete", detail_url(demo_org.esha))

        assert response.status_code == 405


class TestDeactivation:
    def test_hr_deactivates_and_login_stops(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        response = api_write("post", action_url(demo_org.esha, "deactivate"))

        assert response.status_code == 200
        assert response.data["status"] == "inactive"
        demo_org.employee_user.refresh_from_db()
        assert demo_org.employee_user.is_active is False

        login = api_write(
            "post",
            LOGIN_URL,
            {"email": "employee@example.com", "password": "test-pass-12345"},
        )
        assert login.status_code == 400

    def test_deactivation_is_audited_once_and_idempotent(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        api_write("post", action_url(demo_org.esha, "deactivate"))
        api_write("post", action_url(demo_org.esha, "deactivate"))

        rows = AuditLog.objects.filter(
            model="employees.employee", object_id=str(demo_org.esha.pk)
        )
        status_rows = [
            row
            for row in rows
            if "status" in (row.changes.get("changes") or {})
        ]
        assert len(status_rows) == 1
        assert status_rows[0].changes["changes"]["status"] == {
            "before": "active",
            "after": "inactive",
        }

    def test_reactivate_restores_the_login(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)
        api_write("post", action_url(demo_org.esha, "deactivate"))

        response = api_write("post", action_url(demo_org.esha, "reactivate"))

        assert response.status_code == 200
        assert response.data["status"] == "active"
        demo_org.employee_user.refresh_from_db()
        assert demo_org.employee_user.is_active is True

        login = api_write(
            "post",
            LOGIN_URL,
            {"email": "employee@example.com", "password": "test-pass-12345"},
        )
        assert login.status_code == 200

    @pytest.mark.parametrize("role", ["manager", "employee"])
    def test_non_hr_cannot_deactivate(
        self, auth_client, api_write, demo_org, role
    ):
        user = demo_org.manager_user if role == "manager" else demo_org.employee_user
        auth_client(user)

        response = api_write("post", action_url(demo_org.esha, "deactivate"))

        assert response.status_code == 403

    def test_hr_cannot_deactivate_an_admin(
        self, auth_client, api_write, make_employee, demo_org
    ):
        admin_employee = make_employee(
            user=demo_org.admin,
            first_name="Aarti",
            last_name="Admin",
            team=demo_org.sales,
        )
        auth_client(demo_org.hr)

        response = api_write("post", action_url(admin_employee, "deactivate"))

        assert response.status_code == 403

    def test_hr_cannot_reactivate_an_admin(
        self, auth_client, api_write, make_employee, demo_org
    ):
        admin_employee = make_employee(
            user=demo_org.admin,
            first_name="Aarti",
            last_name="Admin",
            status="inactive",
        )
        auth_client(demo_org.hr)

        response = api_write("post", action_url(admin_employee, "reactivate"))

        assert response.status_code == 403


class TestFiltersAndPagination:
    def test_lists_are_paginated(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        response = api_client.get(LIST_URL)

        assert set(response.data) >= {"count", "page", "pages", "results"}

    def test_filter_by_team(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        response = api_client.get(f"{LIST_URL}?team={demo_org.engineering.pk}")

        assert response.data["count"] == 2

    def test_filter_by_status(self, auth_client, api_client, demo_org):
        from apps.employees.models import Employee

        Employee.objects.filter(pk=demo_org.sam.pk).update(status="inactive")
        auth_client(demo_org.hr)

        response = api_client.get(f"{LIST_URL}?status=inactive")

        assert response.data["count"] == 1
        assert response.data["results"][0]["email"] == "sales@example.com"

    def test_filter_by_role(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        response = api_client.get(f"{LIST_URL}?role=manager")

        assert response.data["count"] == 1
        assert response.data["results"][0]["email"] == "manager@example.com"

    def test_search_matches_name_and_email(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        by_name = api_client.get(f"{LIST_URL}?search=meera")
        by_email = api_client.get(f"{LIST_URL}?search=sales@example.com")

        assert by_name.data["count"] == 1
        assert by_email.data["count"] == 1
        assert by_email.data["results"][0]["email"] == "sales@example.com"

    def test_unknown_status_is_rejected(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        response = api_client.get(f"{LIST_URL}?status=holiday")

        assert response.status_code == 400
        assert "status" in response.data["fields"]
