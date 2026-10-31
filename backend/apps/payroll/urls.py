"""Payroll routes under /api/v1/payroll/."""

from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    PayrollDashboardView,
    PayrollRecordViewSet,
    SalaryRevisionViewSet,
    SalaryStructureViewSet,
)

router = SimpleRouter()
router.register(
    "salary-structures", SalaryStructureViewSet, basename="salary-structure"
)
router.register("salary-revisions", SalaryRevisionViewSet, basename="salary-revision")
router.register("records", PayrollRecordViewSet, basename="payroll-record")

urlpatterns = [
    path("dashboard/", PayrollDashboardView.as_view(), name="payroll-dashboard"),
    *router.urls,
]
