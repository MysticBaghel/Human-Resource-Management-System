"""Audit rows: exactly one per action, attributed and diffed."""

from apps.audit.models import AuditLog

EMPLOYEES_URL = "/api/v1/employees/"
TEAMS_URL = "/api/v1/teams/"


def rows_for(model: str, object_id: int):
    """Audit rows for one object, by the model label the API stores."""
    return AuditLog.objects.filter(model=model, object_id=str(object_id))


def employee_rows(employee):
    return rows_for("employees.employee", employee.pk)


def team_rows(team):
    return rows_for("organization.team", team.pk)


class TestEmployeeAudit:
    def test_create_is_recorded_with_the_actor_and_the_new_values(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        response = api_write(
            "post",
            EMPLOYEES_URL,
            {
                "email": "new.hire@example.com",
                "first_name": "New",
                "last_name": "Hire",
                "job_title": "Designer",
                "start_date": "2024-05-06",
                "team": demo_org.engineering.pk,
            },
        )

        row = rows_for("employees.employee", response.data["id"]).get()
        assert row.action == "create"
        assert row.actor == demo_org.hr
        assert row.changes["after"]["first_name"] == "New"
        assert row.changes["after"]["team"] == demo_org.engineering.pk

    def test_update_records_only_the_fields_that_changed(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        api_write(
            "patch",
            f"{EMPLOYEES_URL}{demo_org.esha.pk}/",
            {"job_title": "Staff Engineer"},
        )

        updates = employee_rows(demo_org.esha).filter(action="update")
        assert updates.count() == 1
        assert updates.get().changes["changes"] == {
            "job_title": {
                "before": "Software Engineer",
                "after": "Staff Engineer",
            }
        }
        assert updates.get().actor == demo_org.hr

    def test_role_change_lands_in_the_same_row(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        api_write(
            "patch",
            f"{EMPLOYEES_URL}{demo_org.esha.pk}/",
            {"job_title": "Staff Engineer", "role": "manager"},
        )

        updates = employee_rows(demo_org.esha).filter(action="update")
        assert updates.count() == 1
        changes = updates.get().changes["changes"]
        assert changes["role"] == {"before": "employee", "after": "manager"}
        assert changes["job_title"] == {
            "before": "Software Engineer",
            "after": "Staff Engineer",
        }

    def test_a_save_that_changes_nothing_writes_nothing(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        response = api_write(
            "patch",
            f"{EMPLOYEES_URL}{demo_org.esha.pk}/",
            {"job_title": "Software Engineer"},
        )

        assert response.status_code == 200
        assert employee_rows(demo_org.esha).filter(action="update").count() == 0

    def test_deactivation_is_an_update_row(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        api_write("post", f"{EMPLOYEES_URL}{demo_org.esha.pk}/deactivate/")

        update = employee_rows(demo_org.esha).filter(action="update").get()
        assert update.changes["changes"]["status"] == {
            "before": "active",
            "after": "inactive",
        }


class TestTeamAudit:
    def test_create_is_recorded(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        response = api_write("post", TEAMS_URL, {"name": "Marketing"})

        row = rows_for("organization.team", response.data["id"]).get()
        assert row.action == "create"
        assert row.actor == demo_org.hr
        assert row.changes["after"]["name"] == "Marketing"

    def test_update_writes_exactly_one_row(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        api_write("patch", f"{TEAMS_URL}{demo_org.sales.pk}/", {"name": "Revenue"})

        updates = team_rows(demo_org.sales).filter(action="update")
        assert updates.count() == 1
        assert updates.get().changes["changes"] == {
            "name": {"before": "Sales", "after": "Revenue"}
        }

    def test_delete_is_recorded_with_the_values_it_had(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        api_write("delete", f"{TEAMS_URL}{demo_org.sales.pk}/")

        deleted = team_rows(demo_org.sales).filter(action="delete").get()
        assert deleted.changes["before"]["name"] == "Sales"
        assert deleted.actor == demo_org.hr


class TestAttribution:
    def test_rows_without_a_request_have_no_actor(self, make_employee):
        employee = make_employee(first_name="Back", last_name="Office")

        row = employee_rows(employee).get()

        assert row.action == "create"
        assert row.actor is None

    def test_signing_in_does_not_write_audit_rows(self, auth_client, demo_org):
        before = AuditLog.objects.count()

        auth_client(demo_org.hr)

        assert AuditLog.objects.count() == before

    def test_reading_does_not_write_audit_rows(
        self, auth_client, api_client, demo_org
    ):
        auth_client(demo_org.hr)
        before = AuditLog.objects.count()

        api_client.get(EMPLOYEES_URL)
        api_client.get(f"{EMPLOYEES_URL}{demo_org.esha.pk}/")
        api_client.get(TEAMS_URL)

        assert AuditLog.objects.count() == before
