"""Health endpoint, shared API behaviour, and the User model."""

import pytest


class TestHealth:
    def test_health_returns_ok_without_authentication(self, api_client):
        response = api_client.get("/api/v1/health/")

        assert response.status_code == 200
        assert response.data == {"status": "ok"}


class TestErrorShape:
    """Errors use one shape everywhere: detail, code, fields."""

    def test_unauthenticated_error_uses_the_shared_shape(self, api_client):
        response = api_client.get("/api/v1/auth/me/")

        assert response.status_code in (401, 403)
        assert set(response.data) == {"detail", "code", "fields"}
        assert isinstance(response.data["detail"], str)
        assert isinstance(response.data["code"], str)
        assert isinstance(response.data["fields"], dict)

    def test_validation_error_lists_offending_fields(self, api_client):
        from tests.test_auth import post

        response = post(api_client, "/api/v1/auth/login/", {})

        assert response.status_code == 400
        assert set(response.data) == {"detail", "code", "fields"}
        assert "email" in response.data["fields"]
        assert "password" in response.data["fields"]

    def test_unknown_api_url_uses_the_shared_shape(self, api_client):
        """Unmatched /api/v1/ paths must not fall through to an HTML 404."""
        response = api_client.get("/api/v1/does-not-exist/")

        assert response.status_code == 404
        assert set(response.data) == {"detail", "code", "fields"}


class TestUserModel:
    def test_email_is_the_username_field(self):
        from django.contrib.auth import get_user_model

        assert get_user_model().USERNAME_FIELD == "email"

    def test_create_user_hashes_the_password(self, db, make_user):
        user = make_user("hash-check@example.com")
        assert user.password != "test-pass-12345"
        assert user.check_password("test-pass-12345")

    def test_create_user_requires_an_email(self, db):
        from django.contrib.auth import get_user_model

        with pytest.raises(ValueError):
            get_user_model().objects.create_user(email="", password="x")

    def test_default_role_is_employee(self, db):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            email="default-role@example.com", password="x"
        )
        assert user.role == "employee"

    def test_create_superuser_is_admin_and_staff(self, db):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_superuser(
            email="super@example.com", password="x"
        )
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.role == "admin"

    def test_login_email_is_normalised_to_lowercase(self, db, make_user):
        """A mixed-case address must stay reachable at login."""
        user = make_user("Mixed.Case@Example.COM")

        assert user.email == "mixed.case@example.com"

    def test_email_must_be_unique(self, db, make_user):
        from django.db import IntegrityError

        make_user("duplicate@example.com")
        with pytest.raises(IntegrityError):
            make_user("duplicate@example.com")


class TestRoleScoping:
    """The helper every viewset will use to scope querysets by role.

    The per-role strategies target the Phase 2 models (Employee.team,
    Team.lead), so this covers the fail-closed behaviour that Phase 1 can
    actually exercise.
    """

    def test_unknown_role_is_scoped_to_nothing(self, db, make_user):
        from django.contrib.auth import get_user_model

        from apps.core.scoping import scope_queryset

        make_user("known@example.com")
        user = make_user("odd@example.com")
        user.role = "contractor"

        scoped = scope_queryset(get_user_model().objects.all(), user, scope="own_team")

        assert scoped.count() == 0

    def test_anonymous_user_is_scoped_to_nothing(self, db, make_user):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import AnonymousUser

        from apps.core.scoping import scope_queryset

        make_user("someone@example.com")

        scoped = scope_queryset(
            get_user_model().objects.all(), AnonymousUser(), scope="own_team"
        )

        assert scoped.count() == 0

    def test_empty_queryset_stays_empty(self, db, make_user):
        """Guards the none() vs EmptyQuerySet trap."""
        from django.contrib.auth import get_user_model

        from apps.core.scoping import scope_queryset

        make_user("empty-check@example.com")
        already_empty = get_user_model().objects.none()

        scoped = scope_queryset(already_empty, make_user("role-check@example.com"))

        assert scoped.count() == 0

    def test_unknown_scope_name_raises(self, db, make_user):
        from django.core.exceptions import ImproperlyConfigured

        from apps.core.scoping import scope_queryset

        with pytest.raises(ImproperlyConfigured):
            scope_queryset(None, make_user("scope@example.com"), scope="nonsense")


class TestPermissionClasses:
    """The classes in core/permissions.py behave as named."""

    @pytest.mark.parametrize(
        "permission_name,allowed",
        [
            ("IsAdmin", {"admin"}),
            ("IsHR", {"hr"}),
            ("IsManager", {"manager"}),
            ("IsEmployee", {"employee"}),
            ("IsHROrAdmin", {"hr", "admin"}),
            ("IsManagerOrAbove", {"manager", "hr", "admin"}),
        ],
    )
    def test_permission_matrix(self, db, make_user, permission_name, allowed):
        from apps import core

        permission_class = getattr(core.permissions, permission_name)()
        request = type("Request", (), {})()

        for role in ["admin", "hr", "manager", "employee"]:
            request.user = make_user(f"{role}-{permission_name}@example.com", role=role)
            assert permission_class.has_permission(request, None) is (
                role in allowed
            ), f"{permission_name} mismatch for {role}"

    def test_unauthenticated_is_denied(self, db):
        from django.contrib.auth.models import AnonymousUser

        from apps.core.permissions import IsHROrAdmin

        request = type("Request", (), {"user": AnonymousUser()})()

        assert IsHROrAdmin().has_permission(request, None) is False

    def test_is_read_only_still_requires_authentication(self, db, make_user):
        """A view using this class alone must not admit anonymous readers."""
        from django.contrib.auth.models import AnonymousUser

        from apps.core.permissions import IsReadOnly

        permission = IsReadOnly()
        safe_request = type("Request", (), {"method": "GET", "user": AnonymousUser()})()
        assert permission.has_permission(safe_request, None) is False

        write_request = type(
            "Request",
            (),
            {"method": "POST", "user": make_user("readonly@example.com")},
        )()
        assert permission.has_permission(write_request, None) is False

        read_request = type(
            "Request",
            (),
            {"method": "GET", "user": make_user("reader@example.com")},
        )()
        assert permission.has_permission(read_request, None) is True
