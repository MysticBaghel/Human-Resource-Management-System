"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # auth/ must come before core/, which ends in a catch-all 404 pattern that
    # would otherwise swallow every later path.
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.employees.urls")),
    path("api/v1/", include("apps.organization.urls")),
    path("api/v1/", include("apps.timeoff.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path("api/v1/", include("apps.dashboard.urls")),
    path("api/v1/", include("apps.core.urls")),
]
