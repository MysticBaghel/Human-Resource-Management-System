"""The invite flow: one-time links, expiry and the account they switch on."""

import uuid
from datetime import timedelta

from django.core import mail
from django.utils import timezone

from apps.accounts.models import User
from apps.employees.models import EmployeeInvite

EMPLOYEES_URL = "/api/v1/employees/"
ACCEPT_URL = "/api/v1/auth/accept-invite/"
LOGIN_URL = "/api/v1/auth/login/"
LOGOUT_URL = "/api/v1/auth/logout/"

NEW_PASSWORD = "BrandNewPass!42"


def new_hire_payload(team) -> dict:
    return {
        "email": "new.hire@example.com",
        "first_name": "New",
        "last_name": "Hire",
        "job_title": "Designer",
        "start_date": "2024-05-06",
        "team": team.pk,
    }


def invite_new_hire(api_write, demo_org) -> EmployeeInvite:
    response = api_write("post", EMPLOYEES_URL, new_hire_payload(demo_org.engineering))
    assert response.status_code == 201, response.data
    return EmployeeInvite.objects.get(user__email="new.hire@example.com")


class TestInviteEmail:
    def test_creating_an_employee_emails_one_working_link(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)
        before = len(mail.outbox)

        invite = invite_new_hire(api_write, demo_org)

        sent = mail.outbox[before:]
        assert len(sent) == 1
        assert sent[0].to == ["new.hire@example.com"]
        assert f"/accept-invite?token={invite.token}" in sent[0].body
        assert invite.accepted_at is None
        assert not invite.is_expired

    def test_new_employee_cannot_log_in_before_accepting(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)
        invite_new_hire(api_write, demo_org)

        response = api_write(
            "post",
            LOGIN_URL,
            {"email": "new.hire@example.com", "password": NEW_PASSWORD},
        )

        assert response.status_code == 400


class TestInviteAcceptance:
    def test_accept_sets_the_password_activates_and_signs_in(
        self, auth_client, api_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)
        invite = invite_new_hire(api_write, demo_org)

        response = api_write(
            "post", ACCEPT_URL, {"token": str(invite.token), "password": NEW_PASSWORD}
        )

        assert response.status_code == 200
        assert response.data["email"] == "new.hire@example.com"

        user = User.objects.get(email="new.hire@example.com")
        assert user.is_active is True
        assert user.check_password(NEW_PASSWORD)
        invite.refresh_from_db()
        assert invite.accepted_at is not None

        # Accepting signs the person in, so the app can go straight to the
        # dashboard.
        assert api_client.session.get("_auth_user_id") == str(user.pk)
        assert api_client.get("/api/v1/auth/me/").data["email"] == user.email

    def test_accepted_password_works_on_the_login_page(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)
        invite = invite_new_hire(api_write, demo_org)
        api_write(
            "post", ACCEPT_URL, {"token": str(invite.token), "password": NEW_PASSWORD}
        )
        assert api_write("post", LOGOUT_URL).status_code == 204

        response = api_write(
            "post",
            LOGIN_URL,
            {"email": "new.hire@example.com", "password": NEW_PASSWORD},
        )

        assert response.status_code == 200
        assert response.data["role"] == "employee"

    def test_token_can_only_be_used_once(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)
        invite = invite_new_hire(api_write, demo_org)
        api_write(
            "post", ACCEPT_URL, {"token": str(invite.token), "password": NEW_PASSWORD}
        )

        response = api_write(
            "post", ACCEPT_URL, {"token": str(invite.token), "password": NEW_PASSWORD}
        )

        assert response.status_code == 400
        assert response.data["detail"] == "This invite link is invalid or has expired."

    def test_unknown_token_is_rejected(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        response = api_write(
            "post", ACCEPT_URL, {"token": str(uuid.uuid4()), "password": NEW_PASSWORD}
        )

        assert response.status_code == 400
        assert response.data["detail"] == "This invite link is invalid or has expired."

    def test_expired_token_is_rejected(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)
        invite = invite_new_hire(api_write, demo_org)
        invite.expires_at = timezone.now() - timedelta(minutes=1)
        invite.save(update_fields=["expires_at"])

        response = api_write(
            "post", ACCEPT_URL, {"token": str(invite.token), "password": NEW_PASSWORD}
        )

        assert response.status_code == 400
        assert response.data["detail"] == "This invite link is invalid or has expired."

    def test_deactivated_employee_cannot_accept(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)
        invite = invite_new_hire(api_write, demo_org)
        employee_id = invite.user.employee.pk
        api_write("post", f"{EMPLOYEES_URL}{employee_id}/deactivate/")

        response = api_write(
            "post", ACCEPT_URL, {"token": str(invite.token), "password": NEW_PASSWORD}
        )

        assert response.status_code == 400

    def test_weak_password_is_a_field_error(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)
        invite = invite_new_hire(api_write, demo_org)

        response = api_write(
            "post", ACCEPT_URL, {"token": str(invite.token), "password": "123"}
        )

        assert response.status_code == 400
        assert "password" in response.data["fields"]

    def test_accept_requires_a_csrf_token(self, csrf_client):
        response = csrf_client.post(
            ACCEPT_URL,
            {"token": str(uuid.uuid4()), "password": NEW_PASSWORD},
            format="json",
        )

        assert response.status_code == 403
