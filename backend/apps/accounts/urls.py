"""Auth routes, all under /api/v1/auth/."""

from django.urls import path

from .views import (
    AdminProbeView,
    CsrfView,
    EmployeeProbeView,
    HRProbeView,
    LoginView,
    LogoutView,
    ManagerProbeView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RoleProbeView,
)

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view({"post": "create"}), name="auth-logout"),
    path("me/", MeView.as_view({"get": "list"}), name="auth-me"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    # Role probes: protected endpoints used to prove the API returns 403.
    path("probe/", RoleProbeView.as_view(), name="probe-any"),
    path("probe/admin/", AdminProbeView.as_view(), name="probe-admin"),
    path("probe/hr/", HRProbeView.as_view(), name="probe-hr"),
    path("probe/manager/", ManagerProbeView.as_view(), name="probe-manager"),
    path("probe/employee/", EmployeeProbeView.as_view(), name="probe-employee"),
]
