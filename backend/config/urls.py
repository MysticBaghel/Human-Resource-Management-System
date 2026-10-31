"""Root URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
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
    path("api/v1/payroll/", include("apps.payroll.urls")),
    path("api/v1/", include("apps.invoices.urls")),
    path("api/v1/", include("apps.core.urls")),
]

# In development Django serves uploaded logos. Production must serve MEDIA_ROOT
# (or object storage) at MEDIA_URL through the web server.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
