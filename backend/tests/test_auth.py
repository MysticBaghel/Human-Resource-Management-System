"""Authentication tests: login, logout, me, role permissions, password reset."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()

LOGIN_URL = "/api/v1/auth/login/"
LOGOUT_URL = "/api/v1/auth/logout/"
ME_URL = "/api/v1/auth/me/"
CSRF_URL = "/api/v1/auth/csrf/"
RESET_URL = "/api/v1/auth/password-reset/"
RESET_CONFIRM_URL = "/api/v1/auth/password-reset/confirm/"

PASSWORD = "test-pass-12345"


def csrf_headers(client) -> dict:
    """The token the React client would send as X-CSRFToken."""
    cookie = client.cookies.get("csrftoken")
    return {"HTTP_X_CSRFTOKEN": cookie.value} if cookie else {}


def post(client, path, data):
    """POST JSON with the client's current CSRF token attached."""
    return client.post(path, data, format="json", **csrf_headers(client))


class TestLogin:
    def test_login_succeeds_with_valid_credentials(self, api_client, employee_user):
        response = post(
            api_client,
            LOGIN_URL,
            {"email": employee_user.email, "password": PASSWORD},
        )

        assert response.status_code == 200
        assert response.data["email"] == employee_user.email
        assert response.data["role"] == "employee"
        # A session must actually be established, not just a 200 returned.
        assert api_client.session.get("_auth_user_id") == str(employee_user.pk)
        # The password must never be echoed back.
        assert "password" not in response.data

    def test_login_is_case_insensitive_on_email(self, api_client, employee_user):
        response = post(
            api_client,
            LOGIN_URL,
            {"email": employee_user.email.upper(), "password": PASSWORD},
        )
        assert response.status_code == 200

    def test_login_fails_with_wrong_password(self, api_client, employee_user):
        response = post(
            api_client, LOGIN_URL, {"email": employee_user.email, "password": "wrong"}
        )

        assert response.status_code == 400
        assert response.data["code"] == "invalid"
        assert "_auth_user_id" not in api_client.session

    def test_login_fails_for_unknown_email(self, api_client):
        response = post(
            api_client, LOGIN_URL, {"email": "nobody@example.com", "password": PASSWORD}
        )

        assert response.status_code == 400
        assert response.data["detail"] == "Invalid email or password."

    def test_error_message_does_not_reveal_whether_email_exists(
        self, api_client, employee_user
    ):
        wrong_password = post(
            api_client, LOGIN_URL, {"email": employee_user.email, "password": "wrong"}
        )
        unknown_email = post(
            api_client, LOGIN_URL, {"email": "nobody@example.com", "password": "wrong"}
        )

        assert wrong_password.data["detail"] == unknown_email.data["detail"]

    def test_login_fails_for_deactivated_user(self, api_client, employee_user):
        employee_user.is_active = False
        employee_user.save(update_fields=["is_active"])

        response = post(
            api_client,
            LOGIN_URL,
            {"email": employee_user.email, "password": PASSWORD},
        )

        assert response.status_code == 400
        assert "_auth_user_id" not in api_client.session

    def test_login_requires_email_and_password(self, api_client):
        response = post(api_client, LOGIN_URL, {})

        assert response.status_code == 400
        assert response.data["code"] == "invalid"
        assert set(response.data["fields"]) == {"email", "password"}


class TestLogout:
    def test_logout_clears_the_session(self, api_client, auth_client, employee_user):
        auth_client(employee_user)
        assert "_auth_user_id" in api_client.session

        response = post(api_client, LOGOUT_URL, {})

        assert response.status_code == 204
        assert "_auth_user_id" not in api_client.session

    def test_logout_requires_authentication(self, api_client):
        response = post(api_client, LOGOUT_URL, {})
        assert response.status_code in (401, 403)


class TestMe:
    def test_me_returns_the_current_user(self, api_client, auth_client, hr_user):
        auth_client(hr_user)

        response = api_client.get(ME_URL)

        assert response.status_code == 200
        assert response.data["email"] == hr_user.email
        assert response.data["role"] == "hr"

    def test_me_is_rejected_when_logged_out(self, api_client):
        response = api_client.get(ME_URL)
        assert response.status_code in (401, 403)


class TestRolePermissions:
    """Each role against each protected endpoint.

    The API, not the React sidebar, is the real gate.
    """

    @pytest.mark.parametrize("endpoint", ["admin", "hr", "manager", "employee"])
    @pytest.mark.parametrize("role", ["admin", "hr", "manager", "employee"])
    def test_role_probe(self, api_client, auth_client, make_user, role, endpoint):
        user = make_user(f"{role}-{endpoint}@example.com", role=role)
        auth_client(user)

        response = api_client.get(f"/api/v1/auth/probe/{endpoint}/")

        if role == endpoint:
            assert response.status_code == 200, f"{role} should reach probe/{endpoint}/"
        else:
            assert response.status_code == 403, (
                f"{role} must be forbidden from probe/{endpoint}/"
            )

    def test_probe_requires_authentication(self, api_client):
        response = api_client.get("/api/v1/auth/probe/admin/")
        assert response.status_code in (401, 403)

    def test_any_authenticated_role_reaches_the_shared_probe(
        self, api_client, auth_client, employee_user
    ):
        auth_client(employee_user)

        response = api_client.get("/api/v1/auth/probe/")

        assert response.status_code == 200
        assert response.data["role"] == "employee"

    def test_inactive_user_session_is_rejected(
        self, api_client, auth_client, manager_user
    ):
        """Deactivating a user must stop an existing session being accepted."""
        auth_client(manager_user)
        manager_user.is_active = False
        manager_user.save(update_fields=["is_active"])

        response = api_client.get(ME_URL)
        assert response.status_code in (401, 403)


class TestCsrf:
    def test_csrf_endpoint_sets_the_cookie(self, csrf_client):
        response = csrf_client.get(CSRF_URL)

        assert response.status_code == 200
        assert "csrftoken" in response.cookies

    def test_login_without_csrf_token_is_rejected(self, csrf_client, employee_user):
        """CSRF protection must be active on the public login endpoint.

        DRF's APIView is csrf_exempt and its SessionAuthentication only checks
        CSRF for an already-authenticated user, so this endpoint needs
        csrf_protect explicitly. A client with no cookie and no token must fail.
        """
        response = csrf_client.post(
            LOGIN_URL,
            {"email": employee_user.email, "password": PASSWORD},
            format="json",
        )

        assert response.status_code == 403

    def test_login_succeeds_once_the_csrf_cookie_is_present(
        self, csrf_client, employee_user
    ):
        csrf_client.get(CSRF_URL)
        token = csrf_client.cookies["csrftoken"].value

        response = csrf_client.post(
            LOGIN_URL,
            {"email": employee_user.email, "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 200

    def test_password_reset_without_csrf_token_is_rejected(
        self, csrf_client, employee_user
    ):
        response = csrf_client.post(
            RESET_URL, {"email": employee_user.email}, format="json"
        )

        assert response.status_code == 403


class TestPasswordReset:
    def test_request_sends_email_with_a_link(self, api_client, employee_user):
        response = post(api_client, RESET_URL, {"email": employee_user.email})

        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert employee_user.email in mail.outbox[0].to
        assert "reset-password" in mail.outbox[0].body

    def test_request_for_unknown_email_sends_nothing_but_still_returns_200(
        self, api_client
    ):
        response = post(api_client, RESET_URL, {"email": "nobody@example.com"})

        assert response.status_code == 200
        assert len(mail.outbox) == 0

    def test_confirm_sets_a_new_password(self, api_client, employee_user):
        uid = urlsafe_base64_encode(force_bytes(employee_user.pk))
        token = default_token_generator.make_token(employee_user)

        response = post(
            api_client,
            RESET_CONFIRM_URL,
            {"uid": uid, "token": token, "new_password": "brand-new-pass-9876"},
        )

        assert response.status_code == 200
        employee_user.refresh_from_db()
        assert employee_user.check_password("brand-new-pass-9876")

    def test_confirm_rejects_a_bad_token(self, api_client, employee_user):
        uid = urlsafe_base64_encode(force_bytes(employee_user.pk))

        response = post(
            api_client,
            RESET_CONFIRM_URL,
            {"uid": uid, "token": "not-a-real-token", "new_password": "brand-new-pass-9876"},
        )

        assert response.status_code == 400
        assert response.data["detail"] == "This reset link is invalid or has expired."

    def test_confirm_rejects_a_deactivated_user_without_saying_so(
        self, api_client, employee_user
    ):
        """An inactive account must not be resettable, and must not be revealed."""
        uid = urlsafe_base64_encode(force_bytes(employee_user.pk))
        token = default_token_generator.make_token(employee_user)
        employee_user.is_active = False
        employee_user.save(update_fields=["is_active"])

        response = post(
            api_client,
            RESET_CONFIRM_URL,
            {"uid": uid, "token": token, "new_password": "brand-new-pass-9876"},
        )

        assert response.status_code == 400
        assert response.data["detail"] == "This reset link is invalid or has expired."

        employee_user.refresh_from_db()
        assert not employee_user.check_password("brand-new-pass-9876")

    def test_weak_password_is_rejected_with_a_field_error(self, api_client, employee_user):
        uid = urlsafe_base64_encode(force_bytes(employee_user.pk))
        token = default_token_generator.make_token(employee_user)

        response = post(
            api_client,
            RESET_CONFIRM_URL,
            {"uid": uid, "token": token, "new_password": "123"},
        )

        assert response.status_code == 400
        assert response.data["fields"], "expected the failing field to be reported"


class TestSeedUsers:
    def test_seed_users_creates_all_four_roles(self, db):
        from django.core.management import call_command

        call_command("seed_users")

        roles = set(User.objects.values_list("role", flat=True))
        assert roles == {"admin", "hr", "manager", "employee"}
        assert User.objects.filter(role="employee").count() == 2

    def test_seed_users_recreates_a_working_password(self, db):
        """Re-running the seed must reset the password, not leave a stale one."""
        from django.core.management import call_command

        call_command("seed_users")
        user = User.objects.get(email="hr@hrms.test")
        user.set_password("something-else-entirely")
        user.save(update_fields=["password"])

        call_command("seed_users")

        user.refresh_from_db()
        assert user.check_password("DemoPass123!")

    def test_seed_users_is_idempotent(self, db):
        from django.core.management import call_command

        call_command("seed_users")
        count_after_first = User.objects.count()
        call_command("seed_users")

        assert User.objects.count() == count_after_first

    def test_seeded_users_can_log_in(self, api_client, db):
        from django.core.management import call_command

        call_command("seed_users")

        response = post(
            api_client,
            LOGIN_URL,
            {"email": "admin@hrms.test", "password": "DemoPass123!"},
        )

        assert response.status_code == 200
        assert response.data["role"] == "admin"

    def test_seed_users_creates_teams_and_employee_records(self, db):
        from django.core.management import call_command

        from apps.employees.models import Employee
        from apps.organization.models import Team

        call_command("seed_users")

        assert Team.objects.count() == 2
        assert Employee.objects.count() == 5

        engineering = Team.objects.get(name="Engineering")
        assert engineering.lead is not None
        assert engineering.lead.user.email == "manager@hrms.test"

        esha = Employee.objects.get(user__email="employee@hrms.test")
        assert esha.team == engineering
        assert esha.manager == engineering.lead

    def test_seed_users_is_idempotent_for_teams_and_employees(self, db):
        from django.core.management import call_command

        from apps.employees.models import Employee
        from apps.organization.models import Team

        call_command("seed_users")
        call_command("seed_users")

        assert Team.objects.count() == 2
        assert Employee.objects.count() == 5

    def test_seeded_admin_can_use_the_django_admin(self, client, db):
        """admin@ must be staff *and* superuser, or /admin/ is unusable."""
        from django.core.management import call_command

        call_command("seed_users")

        assert client.login(username="admin@hrms.test", password="DemoPass123!")
        index = client.get("/admin/")
        audit = client.get("/admin/audit/auditlog/")

        assert index.status_code == 200
        assert audit.status_code == 200

    def test_non_admin_roles_are_refused_by_the_django_admin(self, client, db):
        from django.core.management import call_command

        call_command("seed_users")

        assert client.login(username="manager@hrms.test", password="DemoPass123!")
        response = client.get("/admin/")

        # The admin site sends a signed-in non-staff user back to its login
        # page with the "not authorized" message.
        assert response.status_code == 302
        assert response.url.startswith("/admin/login/")
