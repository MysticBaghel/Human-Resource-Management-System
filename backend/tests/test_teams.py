"""Team endpoints: scoping, write permissions, CRUD and member counts."""

import pytest

from apps.organization.models import Team

TEAMS_URL = "/api/v1/teams/"


def detail_url(team) -> str:
    return f"{TEAMS_URL}{team.pk}/"


class TestScoping:
    def test_hr_lists_all_teams(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        response = api_client.get(TEAMS_URL)

        assert response.status_code == 200
        assert response.data["count"] == 2
        assert [row["name"] for row in response.data["results"]] == [
            "Engineering",
            "Sales",
        ]

    def test_manager_lists_only_led_teams(self, auth_client, api_client, demo_org):
        auth_client(demo_org.manager_user)

        response = api_client.get(TEAMS_URL)

        assert response.status_code == 200
        assert [row["name"] for row in response.data["results"]] == ["Engineering"]

    def test_employee_cannot_list_teams(self, auth_client, api_client, demo_org):
        auth_client(demo_org.employee_user)

        response = api_client.get(TEAMS_URL)

        assert response.status_code == 403

    def test_manager_cannot_read_a_team_they_do_not_lead(
        self, auth_client, api_client, demo_org
    ):
        auth_client(demo_org.manager_user)

        response = api_client.get(detail_url(demo_org.sales))

        assert response.status_code == 404

    def test_hr_can_read_any_team(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        response = api_client.get(detail_url(demo_org.sales))

        assert response.status_code == 200
        assert response.data["lead_name"] is None

    def test_logged_out_is_rejected(self, api_client):
        response = api_client.get(TEAMS_URL)

        assert response.status_code in (401, 403)


class TestWrites:
    def test_hr_creates_a_team(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        response = api_write("post", TEAMS_URL, {"name": "Marketing"})

        assert response.status_code == 201
        assert response.data["name"] == "Marketing"
        assert response.data["member_count"] == 0
        assert Team.objects.filter(name="Marketing").exists()

    def test_hr_creates_a_team_with_a_lead(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        response = api_write(
            "post", TEAMS_URL, {"name": "Marketing", "lead": demo_org.sam.pk}
        )

        assert response.status_code == 201
        assert response.data["lead"] == demo_org.sam.pk
        assert response.data["lead_name"] == "Sam Sales"

    def test_duplicate_name_is_rejected_case_insensitively(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        response = api_write("post", TEAMS_URL, {"name": "engineering"})

        assert response.status_code == 400
        assert "name" in response.data["fields"]

    def test_name_is_required(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        response = api_write("post", TEAMS_URL, {"name": "   "})

        assert response.status_code == 400
        assert "name" in response.data["fields"]

    @pytest.mark.parametrize("role", ["manager", "employee"])
    def test_non_hr_cannot_create(self, auth_client, api_write, demo_org, role):
        user = demo_org.manager_user if role == "manager" else demo_org.employee_user
        auth_client(user)

        response = api_write("post", TEAMS_URL, {"name": "Marketing"})

        assert response.status_code == 403

    def test_manager_cannot_change_a_team_they_lead(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.manager_user)

        response = api_write(
            "patch", detail_url(demo_org.engineering), {"name": "Platform"}
        )

        assert response.status_code == 403

    def test_hr_updates_name_and_lead(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        response = api_write(
            "patch",
            detail_url(demo_org.sales),
            {"name": "Revenue", "lead": demo_org.sam.pk},
        )

        assert response.status_code == 200
        assert response.data["name"] == "Revenue"
        assert response.data["lead_name"] == "Sam Sales"

    def test_hr_deletes_a_team_and_members_keep_their_record(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        response = api_write("delete", detail_url(demo_org.sales))

        assert response.status_code == 204
        assert not Team.objects.filter(pk=demo_org.sales.pk).exists()
        demo_org.sam.refresh_from_db()
        assert demo_org.sam.team_id is None

    def test_manager_cannot_delete_a_team(self, auth_client, api_write, demo_org):
        auth_client(demo_org.manager_user)

        response = api_write("delete", detail_url(demo_org.engineering))

        assert response.status_code == 403


class TestQuery:
    def test_member_count_is_annotated(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        response = api_client.get(TEAMS_URL)
        counts = {row["name"]: row["member_count"] for row in response.data["results"]}

        assert counts == {"Engineering": 2, "Sales": 1}

    def test_search_matches_team_name(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        response = api_client.get(f"{TEAMS_URL}?search=engineer")

        assert response.data["count"] == 1
        assert response.data["results"][0]["name"] == "Engineering"

    def test_search_matches_lead_name(self, auth_client, api_client, demo_org):
        auth_client(demo_org.hr)

        response = api_client.get(f"{TEAMS_URL}?search=meera")

        assert response.data["count"] == 1
