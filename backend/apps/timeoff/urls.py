"""Time-off routes under /api/v1/."""

from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import LeaveBalanceViewSet, LeaveCalendarView, LeaveRequestViewSet, LeaveTypeViewSet

router = SimpleRouter()
router.register("leave-types", LeaveTypeViewSet, basename="leavetype")
router.register("leave-balances", LeaveBalanceViewSet, basename="leavebalance")
router.register("leave-requests", LeaveRequestViewSet, basename="leaverequest")

urlpatterns = [
    path("leave-calendar/", LeaveCalendarView.as_view(), name="leave-calendar"),
    *router.urls,
]
