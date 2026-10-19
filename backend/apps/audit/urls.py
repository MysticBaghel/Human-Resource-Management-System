"""Audit log routes under /api/v1/audit-logs/."""

from rest_framework.routers import SimpleRouter

from .views import AuditLogViewSet

router = SimpleRouter()
router.register("audit-logs", AuditLogViewSet, basename="auditlog")

urlpatterns = router.urls
